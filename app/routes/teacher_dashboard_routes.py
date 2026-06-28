# routes/teacher_dashboard_routes.py
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.exam import Exam
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.submission import Submission
from app.services.student_service import get_approved_students

router    = APIRouter(tags=["Teacher Dashboard"])
templates = Jinja2Templates(directory="app/templates")


def _get_teacher(request, db):
    from app.models.teacher import Teacher
    tid = request.session.get("user_id")
    if not tid: return None
    try: return db.query(Teacher).filter(Teacher.id == int(tid)).first()
    except: return None


@router.get("/dashboard/teacher")
def teacher_dashboard(request: Request, q: str = Query(None),
                      semester_id: str = Query(None),
                      db: Session = Depends(get_db)):
    teacher = _get_teacher(request, db)
    if not teacher:
        return RedirectResponse("/auth/login", status_code=303)

    sel_sem = int(semester_id) if semester_id and semester_id.strip().isdigit() else None

    from app.models.subject import subject_teachers
    from sqlalchemy import or_
    m2m_ids  = [r[0] for r in db.execute(
                    subject_teachers.select()
                    .where(subject_teachers.c.teacher_id == teacher.id)).fetchall()]
    subjects = (db.query(Subject)
                .filter(or_(Subject.teacher_id == teacher.id, Subject.id.in_(m2m_ids)))
                .order_by(Subject.name).all())

    subject_data = []
    for subj in subjects:
        students  = get_approved_students(db, subj.id, sel_sem, q)
        sem_map   = {}
        for s in students:
            sem_map.setdefault(s.semester or 0, []).append(s)
        subject_data.append({
            "subject":    subj,
            "sem_groups": [{"semester": sn, "students": stus, "count": len(stus)}
                           for sn, stus in sorted(sem_map.items())],
            "count":      len(students),
        })

    all_subs      = (db.query(Submission).join(Exam, Exam.id == Submission.exam_id)
                     .filter(Exam.teacher_id == teacher.id).all())
    pending_count = sum(1 for s in all_subs if s.status in
                        ("uploaded", "sent_for_marking", "pending_review"))
    graded_count  = sum(1 for s in all_subs if s.status in
                        ("marked", "locked", "returned", "reviewed"))

    return templates.TemplateResponse("Teacher/dashboard.html", {
        "request":             request,
        "teacher":             teacher,
        "subject_data":        subject_data,
        "semesters":           db.query(Semester).order_by(Semester.year_start.desc()).all(),
        "selected_semester":   sel_sem,
        "search_query":        q or "",
        "total_students":      sum(sd["count"] for sd in subject_data),
        "subject_count":       len(subject_data),
        "active_exams":        db.query(Exam).filter(Exam.teacher_id == teacher.id).count(),
        "pending_submissions": pending_count,
        "graded_count":        graded_count,
    })


@router.get("/api/teacher/subject-students")
def subject_students_api(request: Request, subject_id: int = Query(...),
                          semester_id: int = Query(None),
                          db: Session = Depends(get_db)):
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        return JSONResponse({"error": "Subject not found"}, status_code=404)
    students = get_approved_students(db, subject_id, semester_id, None)
    return JSONResponse([{
        "id": s.id, "name": s.name, "code": s.student_code,
        "semester": s.semester,
        "department": s.department.name if s.department else "—",
    } for s in students])