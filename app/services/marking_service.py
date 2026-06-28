# services/marking_service.py
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.mark import Mark
from app.models.question import Question
from app.models.question_mark import QuestionMark
from app.models.submission import Submission
from app.schemas.marking import (
    AdjustMarkPayload, BulkReleasePayload, LockPayload,
    ResolveRemarkPayload, SaveMarksPayload,
    SendDirectoryPayload, SendToAdminPayload,
)


def auto_grade(pct: float) -> str:
    if pct >= 90: return "A"
    if pct >= 80: return "B"
    if pct >= 70: return "C"
    if pct >= 60: return "D"
    return "F"


def get_sub(db: Session, sid: int) -> Submission:
    sub = db.get(Submission, sid)
    if not sub:
        raise HTTPException(404, "Submission not found")
    return sub


def get_or_create_mark(db: Session, sid: int) -> Mark:
    m = db.query(Mark).filter(Mark.submission_id == sid).first()
    if not m:
        m = Mark(submission_id=sid)
        db.add(m)
        db.flush()
    return m


def session_teacher(request):
    return (request.session.get("user_id") or
            request.session.get("id") or
            request.session.get("teacher_id"))


def get_questions(db: Session, submission_id: int) -> dict:
    sub  = get_sub(db, submission_id)
    mark = db.query(Mark).filter(Mark.submission_id == submission_id).first()

    # Advance status if fresh
    if sub.status in ("uploaded", "assigned"):
        sub.status = "sent_for_marking"
        db.commit()
        db.refresh(sub)

    if not sub.exam_id:
        return {
            "questions": [], "total_max": 0, "already_marked": False,
            "status": sub.status, "exam_id": None,
            "mark": mark.to_dict() if mark else None
        }

    # Get deduplicated questions
    all_qs = (db.query(Question)
              .filter(Question.exam_id == sub.exam_id)
              .order_by(Question.question_number, Question.id.desc())
              .all())
    seen = {}
    for q in all_qs:
        if q.question_number is None: continue
        if q.question_number not in seen:
            seen[q.question_number] = q

    questions = sorted(seen.values(), key=lambda q: q.question_number)
    existing  = {qm.question_id: qm for qm in
                 db.query(QuestionMark)
                 .filter(QuestionMark.submission_id == submission_id).all()}
    total_max = 0.0
    result    = []
    for q in questions:
        saved = existing.get(q.id)
        total_max += float(q.max_marks or 0)
        result.append({
            "question_id":     q.id,
            "question_number": q.question_number,
            "text":            q.text,
            "max_marks":       q.max_marks,
            "answer_type":     getattr(q, "answer_type", None),
            "awarded_marks":   saved.awarded_marks if saved else None,
            "comment":         saved.comment       if saved else "",
        })
    return {
        "questions":     result,
        "total_max":     total_max,
        "already_marked": len(existing) > 0,
        "status":        sub.status,
        "exam_id":       sub.exam_id,
        "mark":          mark.to_dict() if mark else None
    }


def save_question_marks(db: Session, submission_id: int,
                        payload: SaveMarksPayload) -> dict:
    sub  = get_sub(db, submission_id)
    mark = db.query(Mark).filter(Mark.submission_id == submission_id).first()

    # No lock check — allow re-marking at any time
    qmap = {q.id: q for q in
            db.query(Question).filter(Question.exam_id == sub.exam_id).all()}

    total_awarded = total_max = 0.0
    for qi in payload.question_marks:
        q = qmap.get(qi.question_id)
        if not q:
            continue  # skip unknown questions gracefully
        amax = float(q.max_marks or 0)
        awarded = min(float(qi.awarded_marks or 0), amax)

        qm = db.query(QuestionMark).filter(
            QuestionMark.submission_id == submission_id,
            QuestionMark.question_id   == qi.question_id).first()
        if qm:
            qm.question_number = q.question_number
            qm.awarded_marks   = awarded
            qm.max_marks       = amax
            qm.comment         = qi.comment or ""
            qm.marked_by       = payload.teacher_id
        else:
            db.add(QuestionMark(
                submission_id=submission_id,
                question_id=qi.question_id,
                question_number=q.question_number,
                awarded_marks=awarded,
                max_marks=amax,
                comment=qi.comment or "",
                marked_by=payload.teacher_id,
                reviewed_by=None,
                review_status="pending",
                is_auto_marked=False,
            ))
        total_awarded += awarded
        total_max     += amax

    pct   = round((total_awarded / total_max) * 100, 2) if total_max > 0 else 0.0
    grade = (payload.letter_grade or "").strip() or auto_grade(pct)

    mark = get_or_create_mark(db, submission_id)
    mark.score        = total_awarded
    mark.max_score    = total_max
    mark.percentage   = pct
    mark.letter_grade = grade
    mark.comments     = payload.feedback   if payload.feedback   is not None else mark.comments
    mark.status       = payload.status     or "marked"
    mark.teacher_id   = payload.teacher_id if payload.teacher_id is not None else mark.teacher_id
    mark.is_locked    = False  # never lock

    if hasattr(mark, "marked_at"):
        mark.marked_at = datetime.now(timezone.utc)

    sub.status = payload.status or "marked"
    db.commit()
    db.refresh(mark)
    return {
        "success":           True,
        "total_awarded":     total_awarded,
        "total_max":         total_max,
        "percentage":        pct,
        "letter_grade":      grade,
        "mark":              mark.to_dict(),
        "submission_status": sub.status
    }


def finish_marking(db: Session, submission_id: int) -> dict:
    sub  = get_sub(db, submission_id)
    mark = get_or_create_mark(db, submission_id)
    mark.status = "marked"
    mark.is_locked = False
    if hasattr(mark, "marked_at"):
        mark.marked_at = datetime.now(timezone.utc)
    sub.status = "marked"
    db.commit()
    db.refresh(mark)
    return {"success": True, "mark": mark.to_dict(), "submission_status": sub.status}


def send_to_student(db: Session, submission_id: int,
                    teacher_id: Optional[int] = None) -> dict:
    """Send paper to student — sets status=returned so student can see it."""
    sub  = get_sub(db, submission_id)
    mark = db.query(Mark).filter(Mark.submission_id == submission_id).first()

    sub.status = "returned"
    if mark:
        mark.status    = "returned"
        mark.is_locked = False
        if hasattr(mark, "released_at"):
            mark.released_at = datetime.now(timezone.utc)
        if teacher_id and not mark.teacher_id:
            mark.teacher_id = teacher_id

    db.commit()
    return {"success": True, "submission_status": "returned"}


def release_grade(db: Session, submission_id: int) -> dict:
    sub  = get_sub(db, submission_id)
    mark = db.query(Mark).filter(Mark.submission_id == submission_id).first()
    if mark:
        mark.status    = "returned"
        mark.is_locked = False
        if hasattr(mark, "released_at"):
            mark.released_at = datetime.now(timezone.utc)
    sub.status = "returned"
    db.commit()
    return {"message": "Grade released", "mark": mark.to_dict() if mark else {}}


def adjust_mark(db: Session, submission_id: int,
                payload: AdjustMarkPayload) -> dict:
    get_sub(db, submission_id)
    mark = db.query(Mark).filter(Mark.submission_id == submission_id).first()
    if not mark:
        raise HTTPException(404, "No mark record found")
    new_score       = min(max(0.0, float(mark.score or 0) + payload.delta),
                          float(mark.max_score or 0) if mark.max_score else float("inf"))
    mark.score      = new_score
    mark.percentage = round((new_score / mark.max_score) * 100, 2) if mark.max_score else 0.0
    mark.letter_grade = auto_grade(mark.percentage)
    if payload.reason:
        sign = "+" if payload.delta >= 0 else ""
        mark.internal_note = (mark.internal_note or "") + \
                             f"\n[Adjusted {sign}{payload.delta}: {payload.reason}]"
    if payload.teacher_id:
        mark.teacher_id = payload.teacher_id
    db.commit()
    db.refresh(mark)
    return {
        "success":       True,
        "new_score":     new_score,
        "percentage":    mark.percentage,
        "letter_grade":  mark.letter_grade,
        "mark":          mark.to_dict()
    }


def lock_marks(db: Session, submission_id: int, payload: LockPayload) -> dict:
    # Kept for backwards compat but does not actually lock
    sub  = get_sub(db, submission_id)
    mark = get_or_create_mark(db, submission_id)
    mark.is_locked = False
    mark.status    = "marked"
    sub.status     = "marked"
    db.commit()
    db.refresh(mark)
    return {"success": True, "mark": mark.to_dict(), "submission_status": sub.status}


def unlock_marks(db: Session, submission_id: int, payload: LockPayload) -> dict:
    sub  = get_sub(db, submission_id)
    mark = get_or_create_mark(db, submission_id)
    mark.is_locked = False
    if mark.status in ("locked", "returned"): mark.status = "marked"
    if sub.status  in ("locked", "returned"): sub.status  = "marked"
    db.commit()
    db.refresh(mark)
    return {"success": True, "mark": mark.to_dict(), "submission_status": sub.status}


def release_bulk(db: Session, payload: BulkReleasePayload) -> dict:
    released = 0
    for sid in payload.submission_ids:
        m   = db.query(Mark).filter(Mark.submission_id == sid).first()
        sub = db.query(Submission).filter(Submission.id == sid).first()
        if not sub: continue
        if m:
            m.status    = "returned"
            m.is_locked = False
        sub.status = "returned"
        released += 1
    db.commit()
    return {"success": True, "released_count": released}


def send_to_students(db: Session, payload: SendDirectoryPayload,
                     teacher_id) -> dict:
    from app.models.exam import Exam
    released = 0
    for sid in payload.submission_ids:
        sub  = db.query(Submission).filter(Submission.id == sid).first()
        mark = db.query(Mark).filter(Mark.submission_id == sid).first()
        if not sub: continue
        if teacher_id:
            exam = db.query(Exam).filter(Exam.id == sub.exam_id).first()
            if exam and exam.teacher_id and exam.teacher_id != int(teacher_id):
                continue
        sub.status = "returned"
        if mark:
            mark.status    = "returned"
            mark.is_locked = False
        released += 1
    db.commit()
    return {"success": True, "released_count": released}


def send_to_admin(db: Session, payload: SendToAdminPayload) -> dict:
    from app.models.exam import Exam
    from app.models.delivery_log import DeliveryLog
    exam = db.query(Exam).filter(Exam.id == payload.exam_id).first()
    if not exam: raise HTTPException(404, "Exam not found")
    subs = db.query(Submission).filter(Submission.exam_id == payload.exam_id).all()
    if not subs: raise HTTPException(400, "No submissions found")
    marked = [s for s in subs if s.status in ("marked", "returned")]
    if not marked: raise HTTPException(400, "No marked submissions yet")
    rows = []
    for sub in marked:
        mark   = db.query(Mark).filter(Mark.submission_id == sub.id).first()
        qmarks = db.query(QuestionMark).filter(QuestionMark.submission_id == sub.id).all()
        rows.append({
            "submission_id": sub.id,
            "score":         mark.score        if mark else None,
            "max_score":     mark.max_score    if mark else None,
            "percentage":    mark.percentage   if mark else None,
            "letter_grade":  mark.letter_grade if mark else "",
            "question_marks": [{"number": qm.question_number,
                                 "awarded": qm.awarded_marks,
                                 "max": qm.max_marks} for qm in qmarks],
        })
    avg_vals = [r["percentage"] for r in rows if r["percentage"] is not None]
    avg      = round(sum(avg_vals) / len(avg_vals), 2) if avg_vals else 0
    log = DeliveryLog(
        exam_id=payload.exam_id, sent_by=None, recipient="admin_inbox",
        status="sent", sent_at=datetime.now(timezone.utc),
        message=json.dumps({
            "note":          (payload.note or "").strip(),
            "exam_title":    exam.title,
            "total_marked":  len(marked),
            "average_pct":   avg
        }),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {
        "ok":              True,
        "delivery_log_id": log.id,
        "total_marked":    len(marked),
        "message":         f"Marks for {len(marked)} student(s) sent to admin."
    }


def resolve_remark(db: Session, remark_id: int,
                   payload: ResolveRemarkPayload) -> dict:
    from app.models.remark_request import RemarkRequest
    rr = db.query(RemarkRequest).filter(RemarkRequest.id == remark_id).first()
    if not rr: raise HTTPException(404, "Remark request not found")
    if payload.decision not in ("resolved", "rejected"):
        raise HTTPException(400, "decision must be resolved or rejected")
    rr.status      = payload.decision
    rr.resolution  = payload.resolution
    rr.resolved_by = payload.resolved_by
    rr.resolved_at = datetime.now(timezone.utc)
    if payload.decision == "resolved":
        sub = db.query(Submission).filter(Submission.id == rr.submission_id).first()
        if sub:
            sub.status = "sent_for_marking"
            mark = db.query(Mark).filter(Mark.submission_id == rr.submission_id).first()
            if mark:
                mark.is_locked = False
                mark.status    = "marked"
    db.commit()
    return {"success": True, "remark": rr.to_dict()}