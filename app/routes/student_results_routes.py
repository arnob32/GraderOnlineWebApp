# routes/student_results_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.mark import Mark
from app.models.question import Question
from app.models.question_mark import QuestionMark
from app.models.submission import Submission
from app.models.student import Student

router    = APIRouter(tags=["Student Results"])
templates = Jinja2Templates(directory="app/templates")


def _get_student(request, db):
    sid  = request.session.get("user_id")
    role = request.session.get("role")
    if not sid or role != "student":
        return None
    try:
        return db.query(Student).filter(Student.id == int(sid)).first()
    except:
        return None


@router.get("/student/results/{submission_id}", response_class=HTMLResponse)
def student_result_detail(submission_id: int, request: Request,
                           db: Session = Depends(get_db)):
    student = _get_student(request, db)
    if not student:
        return RedirectResponse("/student/login", status_code=303)

    sub = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.student_id == student.id,
        Submission.status.in_(["returned", "locked", "reviewed"])
    ).first()

    if not sub:
        raise HTTPException(404, "Result not found or not yet released")

    exam    = getattr(sub, "exam",    None)
    subject = getattr(exam, "subject", None) if exam else None
    mark    = db.query(Mark).filter(Mark.submission_id == submission_id).first()

    # Per-question marks with question text
    qms = (db.query(QuestionMark)
           .filter(QuestionMark.submission_id == submission_id)
           .order_by(QuestionMark.question_number).all())

    # Get question texts
    questions_map = {}
    if sub.exam_id:
        qs = db.query(Question).filter(Question.exam_id == sub.exam_id).all()
        questions_map = {q.id: q for q in qs}

    question_marks = []
    for qm in qms:
        q = questions_map.get(qm.question_id)
        question_marks.append({
            "number":  qm.question_number,
            "text":    getattr(q, "text", "") if q else "",
            "awarded": qm.awarded_marks,
            "max":     qm.max_marks,
            "comment": qm.comment or "",
        })

    pct = None
    if mark:
        if mark.percentage is not None:
            pct = mark.percentage
        elif mark.max_score and mark.max_score > 0:
            pct = round((mark.score or 0) / mark.max_score * 100, 1)

    annotated_url = f"/uploads/download-annotated-pdf/{sub.id}" if sub.file_path else None

    paper = {
        "submission_id":  sub.id,
        "exam_name":      getattr(exam,    "title", None) or f"Exam #{sub.exam_id}",
        "subject_name":   getattr(subject, "name",  None),
        "subject_code":   getattr(subject, "code",  None),
        "status":         sub.status,
        "score":          getattr(mark, "score",        None),
        "max_score":      getattr(mark, "max_score",    None),
        "percentage":     pct,
        "grade":          getattr(mark, "letter_grade", None),
        "feedback":       getattr(mark, "comments",     None),
        "annotated_url":  annotated_url,
        "question_marks": question_marks,
    }

    return templates.TemplateResponse("Student/results_detail.html", {
        "request": request,
        "student": student,
        "paper":   paper,
    })