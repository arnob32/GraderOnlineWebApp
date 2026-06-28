# routes/student_dashboard_routes.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.student import Student
from app.models.submission import Submission
from app.models.mark import Mark
from app.models.question_mark import QuestionMark

router    = APIRouter(tags=["Student Dashboard"])
templates = Jinja2Templates(directory="app/templates")


def _get_student(request, db):
    sid  = request.session.get("user_id")
    role = request.session.get("role")
    if not sid or role != "student": return None
    try: return db.query(Student).filter(Student.id == int(sid)).first()
    except: return None


@router.get("/dashboard/student", response_class=HTMLResponse)
def student_dashboard(request: Request, db: Session = Depends(get_db)):
    student = _get_student(request, db)
    if not student:
        return RedirectResponse("/student/login", status_code=303)

    submissions = (db.query(Submission)
                   .filter(Submission.student_id == student.id)
                   .order_by(Submission.id.desc()).all())

    papers, percentages = [], []
    for sub in submissions:
        exam    = getattr(sub, "exam",    None)
        subject = getattr(exam, "subject", None) if exam else None
        mark    = db.query(Mark).filter(Mark.submission_id == sub.id).first()

        pct = None
        if mark:
            if mark.percentage is not None:
                pct = mark.percentage
            elif mark.max_score and mark.max_score > 0:
                pct = round((mark.score or 0) / mark.max_score * 100, 1)
        if pct is not None:
            percentages.append(pct)

        # Per-question marks — only if released
        question_marks = []
        if sub.status in ("returned", "locked", "reviewed"):
            qms = (db.query(QuestionMark)
                   .filter(QuestionMark.submission_id == sub.id)
                   .order_by(QuestionMark.question_number).all())
            for qm in qms:
                question_marks.append({
                    "number":   qm.question_number,
                    "awarded":  qm.awarded_marks,
                    "max":      qm.max_marks,
                    "comment":  qm.comment or "",
                })

        # Show paper link for any returned submission — route handles file lookup
        annotated_url = None
        if sub.status in ("returned", "locked", "reviewed"):
            annotated_url = f"/uploads/download-annotated-pdf/{sub.id}"

        papers.append({
            "submission_id":  sub.id,
            "exam_name":      getattr(exam,    "title", None) or f"Exam #{sub.exam_id}",
            "subject_name":   getattr(subject, "name",  None),
            "subject_code":   getattr(subject, "code",  None),
            "status":         sub.status or "pending",
            "score":          getattr(mark, "score",        None),
            "max_score":      getattr(mark, "max_score",    None),
            "percentage":     pct,
            "grade":          getattr(mark, "letter_grade", None),
            "feedback":       getattr(mark, "comments",     None),
            "annotated_url":  annotated_url,
            "question_marks": question_marks,
        })

    return templates.TemplateResponse("Student/dashboard.html", {
        "request": request,
        "student": student,
        "papers":  papers,
        "avg_pct": round(sum(percentages)/len(percentages), 1) if percentages else 0,
    })