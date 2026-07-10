# routes/marking_routes.py
import time
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.mark import Mark
from app.models.submission import Submission
from app.schemas.marking import (
    AdjustMarkPayload, BulkReleasePayload, LockPayload,
    ResolveRemarkPayload, SaveMarksPayload,
    SendDirectoryPayload, SendToAdminPayload,
)
from app.services import marking_service
from app.services.submission_service import get_student_directory

router    = APIRouter(tags=["Marking"])
templates = Jinja2Templates(directory="app/templates")

MEDIA_TYPES = {".pdf":"application/pdf",".jpg":"image/jpeg",
               ".jpeg":"image/jpeg",".png":"image/png"}
NO_CACHE    = {"Cache-Control":"no-cache, no-store, must-revalidate",
               "Pragma":"no-cache","Expires":"0"}


def _require_teacher(request: Request):
    uid      = request.session.get("user_id")
    is_admin = request.session.get("is_admin")
    if not uid and not is_admin:
        return RedirectResponse("/auth/login", status_code=303)
    return None


def _student_can_access(request: Request, sub: Submission) -> bool:
    """If the session belongs to a student, they may only access their own
    submission. Teacher/admin sessions (or no student role) pass through,
    preserving the existing teacher workflow."""
    role = request.session.get("role")
    if role == "student":
        return str(sub.student_id) == str(request.session.get("user_id"))
    return True


def _find_file(filename: str):
    safe = Path(filename).name
    matches = []
    for d in ["uploaded_papers", "uploaded_exams", "uploads", "Uploads"]:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            if safe in files:
                matches.append(Path(root) / safe)
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_size)


def _resolve_pdf(fp: str):
    """Find PDF from a stored file_path string (handles Windows backslashes)."""
    if not fp:
        return None
    for candidate in [fp, fp.replace("\\", "/")]:
        p = Path(candidate)
        if p.exists():
            return p
    return _find_file(Path(fp).name)


def _anno_dir(submission_id: int) -> Path:
    return Path("uploaded_papers") / "annotations" / str(submission_id)


# ── HTML pages ──────────────────────────────────────────────────────────────

@router.get("/student-directory", response_class=HTMLResponse)
def student_directory_page(request: Request, db: Session = Depends(get_db)):
    redir = _require_teacher(request)
    if redir: return redir
    from app.models.exam import Exam
    from app.models.subject import Subject
    import json
    tid     = marking_service.session_teacher(request)
    exams_q = db.query(Exam)
    if tid:
        exams_q = exams_q.filter(Exam.teacher_id == int(tid))

    # Pre-load submissions data for the template
    from app.models.student import Student
    from app.models.mark import Mark
    subs = db.query(Submission).order_by(Submission.id.desc()).all()
    papers = []
    for sub in subs:
        exam    = db.get(Exam, sub.exam_id) if sub.exam_id else None
        student = db.get(Student, sub.student_id) if sub.student_id else None
        subject = (db.get(Subject, exam.subject_id)
                   if exam and getattr(exam, "subject_id", None) else None)
        mark    = db.query(Mark).filter(Mark.submission_id == sub.id).first()
        if tid and exam and getattr(exam, "teacher_id", None) and exam.teacher_id != int(tid):
            continue
        name = ""
        if student:
            if hasattr(student, "first_name") and student.first_name:
                name = f"{student.first_name} {student.last_name or ''}".strip()
            else:
                name = getattr(student, "name", "") or ""
        papers.append({
            "submission_id": sub.id,
            "exam_id":       sub.exam_id,
            "exam_title":    exam.title if exam else f"Exam #{sub.exam_id}",
            "subject_id":    getattr(exam, "subject_id", None) if exam else None,
            "subject_name":  subject.name if subject else "",
            "student_id":    sub.student_id,
            "student_name":  name or f"Student #{sub.student_id}",
            "student_code":  getattr(student, "student_code", "") if student else "",
            "student_email": getattr(student, "email", "") if student else "",
            "status":        sub.status or "uploaded",
            "score":         getattr(mark, "score",        None) if mark else None,
            "max_score":     getattr(mark, "max_score",    None) if mark else None,
            "percentage":    getattr(mark, "percentage",   None) if mark else None,
            "letter_grade":  getattr(mark, "letter_grade", "") if mark else "",
            "file_url":      f"/uploads/open-submission/{sub.id}",
            "download_url":  f"/uploads/download-annotated-pdf/{sub.id}",
            "grade_url":     f"/uploads/grade-submission/{sub.id}",
        })

    return templates.TemplateResponse("Teacher/student_directory.html", {
        "request":        request,
        "subjects":       db.query(Subject).order_by(Subject.name).all(),
        "exams":          exams_q.order_by(Exam.title).all(),
        "papers_json":    json.dumps(papers),
    })


@router.get("/uploads/grade-submission/{submission_id}", response_class=HTMLResponse)
def grading_dashboard(submission_id: int, request: Request,
                      teacher_id: Optional[int] = Query(None),
                      db: Session = Depends(get_db)):
    redir = _require_teacher(request)
    if redir: return redir
    from app.models.exam import Exam
    from app.models.student import Student

    sub = db.get(Submission, submission_id)
    if not sub: raise HTTPException(404, "Submission not found")

    exam    = db.get(Exam,    sub.exam_id)    if sub.exam_id    else None
    student = db.get(Student, sub.student_id) if sub.student_id else None

    file_url = f"/uploads/open-submission/{submission_id}?t={int(time.time())}"
    fp_raw   = getattr(sub, "file_path", "") or ""
    filename = Path(fp_raw).name if fp_raw else f"submission_{submission_id}.pdf"

    if not teacher_id:
        m = db.query(Mark).filter(Mark.submission_id == submission_id).first()
        teacher_id = (m.teacher_id if m else None) or \
                     int(request.session.get("user_id") or 0)

    paper_num = total_papers = 1
    next_id   = None
    if exam:
        all_subs = (db.query(Submission).filter(Submission.exam_id == exam.id)
                    .order_by(Submission.id).all())
        ids          = [s.id for s in all_subs]
        paper_num    = (ids.index(submission_id) + 1) if submission_id in ids else 1
        total_papers = len(ids)
        marked_ids   = {m.submission_id for m in
                        db.query(Mark).filter(Mark.submission_id.in_(ids),
                                              Mark.status == "marked").all()}
        nxt     = next((s for s in all_subs
                        if s.id != submission_id and s.id not in marked_ids), None)
        next_id = nxt.id if nxt else None

    if student:
        if hasattr(student, "first_name") and student.first_name:
            student_name = f"{student.first_name} {student.last_name or ''}".strip()
        else:
            student_name = getattr(student, "name", f"Student #{sub.student_id}")
    else:
        student_name = f"Student #{sub.student_id}"

    return templates.TemplateResponse("grading_dashboard.html", {
        "request":          request,
        "submission_id":    submission_id,
        "filename":         filename,
        "file_url":         file_url,
        "teacher_id":       teacher_id,
        "student_name":     student_name,
        "exam_title":       exam.title if exam else f"Exam #{sub.exam_id}",
        "exam_id":          sub.exam_id or 0,
        "paper_num":        paper_num,
        "total_papers":     total_papers,
        "next_id":          next_id,
        "exam_total_marks": exam.total_marks if exam else None,
        "submission_status": sub.status or "uploaded",
    })


@router.get("/uploads/open-submission/{submission_id}")
def open_submission(submission_id: int, request: Request,
                    db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if not sub: raise HTTPException(404, "Submission not found")
    if not _student_can_access(request, sub):
        raise HTTPException(403, "Not allowed")
    fp   = getattr(sub, "file_path", "") or ""
    path = _resolve_pdf(fp)
    if not path or not path.exists():
        raise HTTPException(404, f"File not found: {fp}")
    return Response(path.read_bytes(), media_type="application/pdf",
                    headers={**NO_CACHE, "Content-Disposition": "inline"})


@router.get("/uploads/download-annotated-pdf/{submission_id}")
def download_annotated_pdf(submission_id: int, request: Request,
                           db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if not sub: raise HTTPException(404, "Submission not found")
    if not _student_can_access(request, sub):
        raise HTTPException(403, "Not allowed")
    fp   = getattr(sub, "file_path", "") or ""
    path = _resolve_pdf(fp)
    if not path or not path.exists():
        raise HTTPException(404, "File not found")
    return Response(path.read_bytes(), media_type="application/pdf",
                    headers={**NO_CACHE,
                             "Content-Disposition": f'attachment; filename="result_{submission_id}.pdf"'})


@router.get("/uploads/marking-ui/{submission_id}")
def marking_ui_redirect(submission_id: int, db: Session = Depends(get_db)):
    if not db.get(Submission, submission_id):
        raise HTTPException(404, "Submission not found")
    return RedirectResponse(f"/uploads/grade-submission/{submission_id}")


@router.api_route("/uploads/file/{filename}", methods=["GET", "HEAD"])
def serve_paper_file(request: Request, filename: str, t: str = None):
    path = _find_file(Path(filename).name)
    if not path: raise HTTPException(404, f"File not found: {filename}")
    mime = MEDIA_TYPES.get(Path(filename).suffix.lower(), "application/octet-stream")
    if request.method == "HEAD":
        return Response(b"", media_type=mime,
                        headers={**NO_CACHE, "Content-Length": str(path.stat().st_size)})
    return Response(path.read_bytes(), media_type=mime,
                    headers={**NO_CACHE, "Content-Disposition": "inline"})


# ── Marking API ──────────────────────────────────────────────────────────────
# NOTE: every static /marking/... path MUST be registered before the dynamic
# /marking/{submission_id} routes below, or FastAPI will try to cast the
# path segment to int and return 422. (This is why /marking/setup-db lives
# here now instead of at the bottom of the file.)

@router.get("/marking/setup-db")
def setup_db():
    from app.database import engine, Base
    try:
        Base.metadata.create_all(engine)
        return {"ok": True, "message": "Tables created"}
    except Exception as e:
        raise HTTPException(500, f"DB setup failed: {e}")


@router.get("/marking/summary-page", response_class=HTMLResponse)
def marking_summary_page(request: Request):
    redir = _require_teacher(request)
    if redir: return redir
    return templates.TemplateResponse("marking_summary.html", {"request": request})


@router.get("/marking/next-paper")
def next_paper(request: Request, exam_id: Optional[int] = Query(None),
               db: Session = Depends(get_db)):
    from app.models.exam import Exam
    tid  = marking_service.session_teacher(request)
    q    = db.query(Submission).join(Exam, Exam.id == Submission.exam_id)
    if tid: q = q.filter(Exam.teacher_id == int(tid))
    if exam_id: q = q.filter(Submission.exam_id == exam_id)
    subs = q.order_by(Submission.id).all()
    if not subs: return RedirectResponse("/uploads/uploaded-exams", status_code=303)
    marked = {m.submission_id for m in
              db.query(Mark).filter(Mark.submission_id.in_([s.id for s in subs]),
                                    Mark.status == "marked").all()}
    pending = [s for s in subs if s.id not in marked]
    if not pending: return RedirectResponse("/student-directory", status_code=303)
    return RedirectResponse(f"/uploads/grade-submission/{pending[0].id}", status_code=303)


@router.get("/marking/queue-status")
def queue_status(request: Request, exam_id: Optional[int] = Query(None),
                 db: Session = Depends(get_db)):
    from app.models.exam import Exam
    tid  = marking_service.session_teacher(request)
    q    = db.query(Submission).join(Exam, Exam.id == Submission.exam_id)
    if tid: q = q.filter(Exam.teacher_id == int(tid))
    if exam_id: q = q.filter(Submission.exam_id == exam_id)
    subs = q.order_by(Submission.id).all()
    if not subs: return {"total": 0, "done": 0, "pending": 0, "next_id": None}
    ids     = [s.id for s in subs]
    marked  = {m.submission_id for m in
               db.query(Mark).filter(Mark.submission_id.in_(ids),
                                     Mark.status == "marked").all()}
    pending = [s for s in subs if s.id not in marked]
    return {"total": len(subs), "done": len(marked),
            "pending": len(pending), "next_id": pending[0].id if pending else None}


@router.get("/marking/teachers")
def get_teachers(db: Session = Depends(get_db)):
    try:
        from app.models.teacher import Teacher
        return [{"id": t.id, "name": t.name}
                for t in db.query(Teacher).order_by(Teacher.first_name).all()]
    except Exception:
        return []


@router.get("/marking/summary")
def grading_summary(status: Optional[str] = Query(None),
                    teacher_id: Optional[int] = Query(None),
                    db: Session = Depends(get_db)):
    from app.models.student import Student
    from app.models.exam import Exam
    q = db.query(Mark, Submission).join(Submission, Submission.id == Mark.submission_id)
    if status:     q = q.filter(Mark.status     == status)
    if teacher_id: q = q.filter(Mark.teacher_id == teacher_id)
    rows = q.order_by(Mark.updated_at.desc()).all()
    student_ids  = {sub.student_id for _, sub in rows if sub.student_id}
    exam_ids     = {sub.exam_id    for _, sub in rows if sub.exam_id}
    students_map = {s.id: s for s in db.query(Student)
                    .filter(Student.id.in_(student_ids)).all()} if student_ids else {}
    exams_map    = {e.id: e for e in db.query(Exam)
                    .filter(Exam.id.in_(exam_ids)).all()} if exam_ids else {}
    results = []
    for mark, sub in rows:
        student = students_map.get(sub.student_id)
        exam    = exams_map.get(sub.exam_id)
        item    = mark.to_dict()
        item.update({
            "submission_id": sub.id, "exam_id": sub.exam_id,
            "student_name":  student.name if student else f"Student #{sub.student_id}",
            "student_code":  getattr(student, "student_code", "") if student else "",
            "student_email": getattr(student, "email", "") if student else "",
            "exam_title":    exam.title if exam else f"Exam #{sub.exam_id}",
            "status":        sub.status,
        })
        results.append(item)
    return {"total": len(results), "results": results}


@router.post("/marking/release-bulk")
def release_bulk(payload: BulkReleasePayload, db: Session = Depends(get_db)):
    return marking_service.release_bulk(db, payload)


@router.get("/marking/{submission_id}/questions")
def get_questions(submission_id: int, db: Session = Depends(get_db)):
    return marking_service.get_questions(db, submission_id)


@router.post("/marking/{submission_id}/questions")
def save_question_marks(submission_id: int, payload: SaveMarksPayload,
                        db: Session = Depends(get_db)):
    return marking_service.save_question_marks(db, submission_id, payload)


@router.post("/marking/{submission_id}/finish")
def finish_marking_api(submission_id: int, db: Session = Depends(get_db)):
    return marking_service.finish_marking(db, submission_id)


@router.post("/marking/{submission_id}/send-to-student")
def send_to_student(submission_id: int, request: Request,
                    db: Session = Depends(get_db)):
    teacher_id = marking_service.session_teacher(request)
    return marking_service.send_to_student(db, submission_id,
                                           int(teacher_id) if teacher_id else None)


@router.post("/marking/{submission_id}/release")
def release_grade(submission_id: int, db: Session = Depends(get_db)):
    return marking_service.release_grade(db, submission_id)


@router.post("/marking/{submission_id}/adjust-mark")
def adjust_mark(submission_id: int, payload: AdjustMarkPayload,
                db: Session = Depends(get_db)):
    return marking_service.adjust_mark(db, submission_id, payload)


@router.post("/marking/{submission_id}/lock")
def lock_marks(submission_id: int, payload: LockPayload,
               db: Session = Depends(get_db)):
    return marking_service.lock_marks(db, submission_id, payload)


@router.post("/marking/{submission_id}/unlock")
def unlock_marks(submission_id: int, payload: LockPayload,
                 db: Session = Depends(get_db)):
    return marking_service.unlock_marks(db, submission_id, payload)


# ── Annotation: auto-save page as teacher draws ──────────────────────────────

@router.post("/marking/{submission_id}/save-annotation-page")
async def save_annotation_page(submission_id: int, request: Request,
                                db: Session = Depends(get_db)):
    """Auto-save a single annotation PNG to disk as teacher draws.
    Called in background from JS after every saveAnnotationSnap()."""
    try:
        form      = await request.form()
        page_num  = int(form.get("page", 0))
        img_field = form.get("image")
        if not page_num or not img_field:
            return JSONResponse({"success": False, "error": "Missing page or image"})
        img_bytes = await img_field.read()
        if not img_bytes:
            return JSONResponse({"success": False, "error": "Empty image"})
        anno_dir = _anno_dir(submission_id)
        anno_dir.mkdir(parents=True, exist_ok=True)
        (anno_dir / f"page_{page_num}.png").write_bytes(img_bytes)
        print(f"[Anno] Saved page {page_num} ({len(img_bytes)} bytes) sub={submission_id}")
        return JSONResponse({"success": True, "page": page_num})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@router.post("/marking/{submission_id}/delete-annotation-page")
async def delete_annotation_page(submission_id: int, request: Request):
    """Delete a saved annotation PNG when the teacher clears a page.
    Without this, embed-from-saved would re-embed annotations the teacher
    explicitly cleared in the UI (server file outlived the localStorage copy)."""
    try:
        form     = await request.form()
        page_num = int(form.get("page", 0))
        if not page_num:
            return JSONResponse({"success": False, "error": "Missing page"})
        anno_dir = _anno_dir(submission_id)
        f = anno_dir / f"page_{page_num}.png"
        if f.exists():
            f.unlink()
        # tidy up empty dir
        try:
            if anno_dir.exists() and not any(anno_dir.iterdir()):
                anno_dir.rmdir()
        except OSError:
            pass
        return JSONResponse({"success": True, "page": page_num})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


# ── Annotation: embed saved pages into PDF on Finish ─────────────────────────

@router.post("/marking/{submission_id}/embed-from-saved")
async def embed_from_saved(submission_id: int, db: Session = Depends(get_db)):
    """Read all saved annotation PNGs and embed them into the submission PDF."""
    import shutil as _sh
    from pathlib import Path as _P

    sub = db.get(Submission, submission_id)
    if not sub: raise HTTPException(404, "Submission not found")

    anno_dir   = _anno_dir(submission_id)
    anno_files = sorted(anno_dir.glob("page_*.png")) if anno_dir.exists() else []

    if not anno_files:
        return JSONResponse({"success": True, "pages_annotated": 0,
                             "note": "No annotation pages saved"})

    page_images = {}
    for f in anno_files:
        try:
            page_images[int(f.stem.replace("page_", ""))] = f.read_bytes()
        except Exception as e:
            print(f"[Anno] Skip {f.name}: {e}")

    if not page_images:
        return JSONResponse({"success": False, "error": "No valid pages"})

    fp       = getattr(sub, "file_path", "") or ""
    pdf_path = _resolve_pdf(fp)
    if not pdf_path or not pdf_path.exists():
        return JSONResponse({"success": False, "error": f"PDF not found: {fp}"})

    try:
        import fitz
        from PIL import Image as _PIL
        import io as _io

        backup = _P(str(pdf_path) + ".bak")
        _sh.copy2(str(pdf_path), str(backup))

        doc      = fitz.open(str(pdf_path))
        new_doc  = fitz.open()
        embedded = 0
        failed   = []

        for pg_idx in range(len(doc)):
            orig   = doc[pg_idx]
            pg_num = pg_idx + 1
            if pg_num in page_images:
                try:
                    # Skip fully-transparent annotation PNGs (blank pages
                    # saved by auto-save) — keep the original vector page.
                    anno_img = _PIL.open(_io.BytesIO(page_images[pg_num])).convert("RGBA")
                    if anno_img.getchannel("A").getbbox() is None:
                        print(f"[Anno] Page {pg_num} annotation blank, keeping original")
                        new_doc.insert_pdf(doc, from_page=pg_idx, to_page=pg_idx)
                        continue

                    # Step 1: rasterize original PDF page to PNG bytes using fitz
                    pix = orig.get_pixmap(matrix=fitz.Matrix(150/72, 150/72), alpha=False)

                    # Get PNG bytes - try multiple methods for compatibility
                    pdf_png = None
                    try:
                        pdf_png = pix.tobytes()          # default PNG in modern fitz
                    except Exception:
                        pass
                    if not pdf_png:
                        try:
                            pdf_png = pix.tobytes("png")  # older fitz
                        except Exception:
                            pass
                    if not pdf_png:
                        try:
                            import tempfile, os as _os2
                            tf = tempfile.mktemp(suffix=".png")
                            pix.save(tf)
                            with open(tf, "rb") as fh:
                                pdf_png = fh.read()
                            _os2.unlink(tf)
                        except Exception:
                            pass

                    if not pdf_png:
                        raise ValueError("Cannot rasterize page")

                    # Step 2: composite using PIL
                    pdf_img = _PIL.open(_io.BytesIO(pdf_png)).convert("RGBA")

                    if anno_img.size != pdf_img.size:
                        anno_img = anno_img.resize(pdf_img.size, _PIL.LANCZOS)

                    comp = _PIL.alpha_composite(pdf_img, anno_img)

                    buf = _io.BytesIO()
                    comp.convert("RGB").save(buf, format="PNG")

                    new_page = new_doc.new_page(width=orig.rect.width, height=orig.rect.height)
                    new_page.insert_image(new_page.rect, stream=buf.getvalue())
                    embedded += 1
                    print(f"[Anno] Embedded page {pg_num} OK ({len(buf.getvalue())} bytes)")

                except Exception as e:
                    import traceback; traceback.print_exc()
                    print(f"[Anno] Page {pg_num} FAILED: {e}")
                    failed.append(pg_num)
                    new_doc.insert_pdf(doc, from_page=pg_idx, to_page=pg_idx)
            else:
                new_doc.insert_pdf(doc, from_page=pg_idx, to_page=pg_idx)

        doc.close()

        if embedded > 0 and not failed:
            tmp = _P(str(pdf_path) + ".tmp")
            new_doc.save(str(tmp), incremental=False, deflate=True)
            new_doc.close()
            if tmp.exists() and tmp.stat().st_size > 0:
                import os as _os
                _os.replace(str(tmp), str(pdf_path))
                backup.unlink(missing_ok=True)
                _sh.rmtree(str(anno_dir), ignore_errors=True)
                print(f"[Anno] Done: {pdf_path} ({pdf_path.stat().st_size} bytes)")
                return JSONResponse({"success": True, "pages_annotated": embedded})

        # Partial failure: do NOT overwrite the PDF with a half-annotated copy.
        # Keep the saved PNGs so the teacher can retry, and report the failure.
        new_doc.close()
        _sh.copy2(str(backup), str(pdf_path))
        backup.unlink(missing_ok=True)
        return JSONResponse({"success": False,
                             "error": "Embed failed",
                             "failed_pages": failed,
                             "pages_annotated": 0})

    except Exception as e:
        import traceback; traceback.print_exc()
        try:
            backup = _P(str(pdf_path) + ".bak")
            if backup.exists(): _sh.copy2(str(backup), str(pdf_path)); backup.unlink()
        except: pass
        return JSONResponse({"success": False, "error": str(e)})


@router.post("/marking/{submission_id}")
def mark_exam(submission_id: int,
              marks:             float         = Form(..., ge=0),
              max_score:         float         = Form(100.0, gt=0),
              letter_grade:      str           = Form(""),
              feedback:          str           = Form(""),
              internal_note:     str           = Form(""),
              submission_status: str           = Form("marked", alias="status"),
              teacher_id:        Optional[int] = Form(None),
              db: Session = Depends(get_db)):
    sub  = marking_service.get_sub(db, submission_id)
    mark = db.query(Mark).filter(Mark.submission_id == submission_id).first()
    if not mark:
        mark = Mark(submission_id=submission_id, teacher_id=teacher_id)
        db.add(mark)
    pct               = round((marks / max_score) * 100, 2) if max_score else 0.0
    mark.score        = marks
    mark.max_score    = max_score
    mark.percentage   = pct
    mark.letter_grade = letter_grade.strip() or marking_service.auto_grade(pct)
    mark.comments     = feedback or None
    mark.internal_note= internal_note or None
    mark.status       = submission_status
    mark.is_locked    = False
    mark.teacher_id   = teacher_id if teacher_id is not None else mark.teacher_id
    if hasattr(mark, "marked_at"):
        mark.marked_at = datetime.now(timezone.utc)
    sub.status = submission_status
    db.commit()
    db.refresh(mark)
    return {"message": "Graded", "mark": mark.to_dict()}


@router.get("/marking/{submission_id}")
def get_mark(submission_id: int, db: Session = Depends(get_db)):
    mark = db.query(Mark).filter(Mark.submission_id == submission_id).first()
    if not mark: raise HTTPException(404, "No grade found")
    return mark.to_dict()


@router.get("/api/student-directory")
def student_directory_api(request: Request,
                           subject_id: Optional[int] = Query(None),
                           exam_id:    Optional[int] = Query(None),
                           status:     Optional[str] = Query(None),
                           db: Session = Depends(get_db)):
    from app.models.exam import Exam
    from app.models.student import Student
    from app.models.subject import Subject
    tid = marking_service.session_teacher(request)
    q   = db.query(Submission).order_by(Submission.id.desc())
    if exam_id: q = q.filter(Submission.exam_id == exam_id)
    if status:  q = q.filter(Submission.status  == status)
    subs   = q.all()
    result = []
    for sub in subs:
        exam    = db.get(Exam,    sub.exam_id)    if sub.exam_id    else None
        student = db.get(Student, sub.student_id) if sub.student_id else None
        subject = (db.get(Subject, exam.subject_id)
                   if exam and getattr(exam, "subject_id", None) else None)
        mark    = db.query(Mark).filter(Mark.submission_id == sub.id).first()
        if tid and exam and getattr(exam, "teacher_id", None) and exam.teacher_id != int(tid):
            continue
        if subject_id and (not subject or subject.id != subject_id):
            continue
        name = ""
        if student:
            if hasattr(student, "first_name") and student.first_name:
                name = f"{student.first_name} {student.last_name or ''}".strip()
            else:
                name = getattr(student, "name", "") or ""
        result.append({
            "submission_id": sub.id,
            "exam_id":       sub.exam_id,
            "exam_title":    exam.title if exam else f"Exam #{sub.exam_id}",
            "subject_id":    getattr(exam, "subject_id", None) if exam else None,
            "subject_name":  subject.name if subject else "",
            "student_id":    sub.student_id,
            "student_name":  name or f"Student #{sub.student_id}",
            "student_code":  getattr(student, "student_code", "") if student else "",
            "student_email": getattr(student, "email", "") if student else "",
            "status":        sub.status or "uploaded",
            "score":         getattr(mark, "score",        None) if mark else None,
            "max_score":     getattr(mark, "max_score",    None) if mark else None,
            "percentage":    getattr(mark, "percentage",   None) if mark else None,
            "letter_grade":  getattr(mark, "letter_grade", "") if mark else "",
            "file_url":      f"/uploads/open-submission/{sub.id}",
            "download_url":  f"/uploads/download-annotated-pdf/{sub.id}",
            "grade_url":     f"/uploads/grade-submission/{sub.id}",
        })
    return result


@router.post("/api/student-directory/send")
def send_to_students(payload: SendDirectoryPayload, request: Request,
                     db: Session = Depends(get_db)):
    tid = marking_service.session_teacher(request)
    return marking_service.send_to_students(db, payload, tid)


@router.post("/api/student-directory/send-to-admin")
def send_to_admin(payload: SendToAdminPayload, db: Session = Depends(get_db)):
    return marking_service.send_to_admin(db, payload)


@router.get("/api/exam/{exam_id}/download-zip")
def download_exam_zip(exam_id: int, request: Request, db: Session = Depends(get_db)):
    from app.models.exam import Exam
    from app.models.student import Student
    from app.utils.zip_exporter import zip_exam_annotated_pdfs
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam: raise HTTPException(404, "Exam not found")
    subs = db.query(Submission).filter(Submission.exam_id == exam_id).all()
    if not subs: raise HTTPException(404, "No submissions found")
    ids      = [s.id for s in subs]
    marks    = {m.submission_id: m for m in
                db.query(Mark).filter(Mark.submission_id.in_(ids)).all()}
    students = {s.id: s for s in db.query(Student)
                .filter(Student.id.in_({s.student_id for s in subs})).all()}
    zip_bytes = zip_exam_annotated_pdfs(
        exam_id=exam_id, exam_title=exam.title,
        submissions=subs, marks=marks, students=students)
    safe_title = "".join(c for c in exam.title if c.isalnum() or c in " -_")[:40].strip()
    return Response(content=zip_bytes, media_type="application/zip",
                    headers={"Content-Disposition":
                             f'attachment; filename="{safe_title or f"exam_{exam_id}"}_annotated.zip"'})


@router.get("/remark/teacher", response_class=HTMLResponse)
def teacher_remark_list(request: Request, db: Session = Depends(get_db)):
    try:
        from app.models.remark_request import RemarkRequest
        remarks = db.query(RemarkRequest).order_by(RemarkRequest.created_at.desc()).all()
    except Exception:
        remarks = []
    return templates.TemplateResponse("remark_requests.html",
                                      {"request": request, "requests": remarks})


@router.post("/remark/{remark_id}/resolve")
def resolve_remark(remark_id: int, payload: ResolveRemarkPayload,
                   db: Session = Depends(get_db)):
    return marking_service.resolve_remark(db, remark_id, payload)