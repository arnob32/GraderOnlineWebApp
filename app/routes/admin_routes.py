from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.department import Department
from app.models.exam import Exam
from app.models.semester import Semester
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.services import admin_service

router    = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def _is_admin(request): return request.session.get("is_admin") is True
def _guard(request):
    if not _is_admin(request): return RedirectResponse("/admin/login", 303)
def _r(request, template, **kw):
    return templates.TemplateResponse(f"Admin/{template}", {"request": request, **kw})

# ── Auth ──────────────────────────────────────────────────────────────────────

@router.get("/login")
def login_page(request: Request):
    if _is_admin(request): return RedirectResponse("/admin/dashboard", 303)
    return _r(request, "login.html")

@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["is_admin"] = True
        return RedirectResponse("/admin/dashboard", 303)
    return _r(request, "login.html", error="Invalid credentials")

@router.get("/logout")
def logout(request: Request):
    request.session.pop("is_admin", None)
    return RedirectResponse("/admin/login", 303)

# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    return _r(request, "dashboard.html",
        total_departments = db.query(Department).count(),
        total_semesters   = db.query(Semester).count(),
        total_subjects    = db.query(Subject).count(),
        total_teachers    = db.query(Teacher).count(),
        pending_teachers  = db.query(Teacher).filter(Teacher.is_approved == False).count(),
        total_students    = db.query(Student).count(),
        total_exams       = db.query(Exam).count(),
    )

# ── Departments ───────────────────────────────────────────────────────────────

@router.get("/departments")
def departments(request: Request, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    return _r(request, "departments.html",
              departments=db.query(Department).order_by(Department.name).all())

@router.post("/departments/create")
def create_department(request: Request, name: str = Form(...), db: Session = Depends(get_db)):
    if r := _guard(request): return r
    name = name.strip()
    if name and not db.query(Department).filter(Department.name == name).first():
        db.add(Department(name=name)); db.commit()
    return RedirectResponse("/admin/departments", 303)

@router.post("/departments/{dept_id}/delete")
def delete_department(request: Request, dept_id: int, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if dept: db.delete(dept); db.commit()
    return RedirectResponse("/admin/departments", 303)

# ── Semesters ─────────────────────────────────────────────────────────────────

@router.get("/semesters")
def semesters(request: Request, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    return _r(request, "semesters.html",
              semesters=db.query(Semester).order_by(Semester.year_start.desc()).all())

@router.post("/semesters/create")
def create_semester(request: Request, name: str = Form(...),
                    year_start: int = Form(...), term: str = Form(...),
                    db: Session = Depends(get_db)):
    if r := _guard(request): return r
    admin_service.create_semester(db, name, year_start, term)
    return RedirectResponse("/admin/semesters", 303)

@router.post("/semesters/{sem_id}/delete")
def delete_semester(request: Request, sem_id: int, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    admin_service.delete_semester(db, sem_id)
    return RedirectResponse("/admin/semesters", 303)

# ── Subjects ──────────────────────────────────────────────────────────────────

@router.get("/subjects")
def subjects(request: Request, dept_id: str | None = None,
             sem_id: str | None = None, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    dept_id_int = int(dept_id) if dept_id and dept_id.strip().isdigit() else None
    sem_id_int  = int(sem_id)  if sem_id  and sem_id.strip().isdigit()  else None
    from app.models.subject import subject_departments
    from sqlalchemy import or_, exists
    q = db.query(Subject)
    if dept_id_int:
        m2m = exists().where(
            (subject_departments.c.subject_id    == Subject.id) &
            (subject_departments.c.department_id == dept_id_int))
        q = q.filter(or_(Subject.department_id == dept_id_int, m2m))
    if sem_id_int:
        q = q.filter(Subject.semester_id == sem_id_int)
    return _r(request, "subjects.html",
        subjects    = q.all(),
        departments = db.query(Department).order_by(Department.name).all(),
        semesters   = db.query(Semester).order_by(Semester.year_start.desc()).all(),
        teachers    = db.query(Teacher).filter(Teacher.is_approved == True).all(),
        sel_dept=dept_id_int, sel_sem=sem_id_int)

@router.post("/subjects/create")
async def create_subject(request: Request, name: str = Form(...),
                         code: str = Form(...), semester_id: int = Form(...),
                         db: Session = Depends(get_db)):
    if r := _guard(request): return r
    form     = await request.form()
    raw_ids  = form.getlist("department_ids")
    dept_ids = [int(x) for x in raw_ids if str(x).isdigit()]
    admin_service.create_subject(
        db, name=name, code=code,
        department_id=dept_ids[0] if dept_ids else None,
        semester_id=semester_id,
        is_elective=form.get("is_elective","false").lower() in ("true","1","on"),
        department_ids=dept_ids)
    return RedirectResponse("/admin/subjects", 303)

@router.post("/subjects/{subject_id}/assign")
def assign_teacher(request: Request, subject_id: int,
                   teacher_id: int = Form(...), db: Session = Depends(get_db)):
    if r := _guard(request): return r
    admin_service.assign_teacher_to_subject(db, subject_id, teacher_id)
    return RedirectResponse("/admin/subjects", 303)

@router.post("/subjects/{subject_id}/delete")
def delete_subject(request: Request, subject_id: int, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    admin_service.delete_subject(db, subject_id)
    return RedirectResponse("/admin/subjects", 303)

# ── Teachers ──────────────────────────────────────────────────────────────────

@router.get("/teachers")
def teachers(request: Request, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    return _r(request, "teachers.html",
        pending     = db.query(Teacher).filter(Teacher.is_approved == False).all(),
        approved    = db.query(Teacher).filter(Teacher.is_approved == True).all(),
        departments = db.query(Department).all())

@router.post("/teachers/{teacher_id}/approve")
def approve_teacher(request: Request, teacher_id: int, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    admin_service.approve_teacher(db, teacher_id)
    return RedirectResponse("/admin/teachers", 303)

@router.post("/teachers/{teacher_id}/reject")
def reject_teacher(request: Request, teacher_id: int, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    admin_service.reject_teacher(db, teacher_id)
    return RedirectResponse("/admin/teachers", 303)

@router.post("/teachers/create")
async def create_teacher(request: Request, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    form    = await request.form()
    fname   = str(form.get("first_name","")).strip()
    lname   = str(form.get("last_name","")).strip()
    email   = str(form.get("email","")).strip()
    passwd  = str(form.get("password","")).strip()
    dept_id = form.get("department_id")
    if fname and lname and email:
        try:
            from app.services.auth_service import signup_teacher
            signup_teacher(db, fname, lname, email, passwd or "teacher123",
                          "", int(dept_id) if dept_id else None)
            t = db.query(Teacher).filter(Teacher.email == email).first()
            if t: t.is_approved = True; db.commit()
        except Exception: pass
    return RedirectResponse("/admin/teachers", 303)

# ── Students ──────────────────────────────────────────────────────────────────

@router.get("/students")
def students(request: Request, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    return _r(request, "students.html",
              students=db.query(Student).all(),
              departments=db.query(Department).all())

# ── Exams ─────────────────────────────────────────────────────────────────────

@router.get("/exams")
def exams(request: Request, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    from sqlalchemy.orm import joinedload
    exams_list = (db.query(Exam)
        .options(joinedload(Exam.teacher), joinedload(Exam.subject),
                 joinedload(Exam.submissions))
        .order_by(Exam.id.desc()).all())
    return _r(request, "exams.html", exams=exams_list)

@router.get("/exams-api")
def exams_api(request: Request, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    result = []
    for e in db.query(Exam).order_by(Exam.id.desc()).all():
        dept = db.query(Department).filter(
            Department.id == e.department_id).first() if e.department_id else None
        result.append({"id": e.id, "title": e.title,
                        "subject_id": getattr(e,"subject_id",None),
                        "teacher_id": e.teacher_id,
                        "department_id": e.department_id,
                        "department_name": dept.name if dept else ""})
    return JSONResponse({"exams": result})

# ── Marking overview ──────────────────────────────────────────────────────────

@router.get("/marking-overview")
def marking_overview(request: Request, db: Session = Depends(get_db)):
    if r := _guard(request): return r
    from app.models.submission import Submission
    from app.models.mark import Mark
    exams = db.query(Exam).order_by(Exam.id.desc()).all()
    rows  = []
    for e in exams:
        subs    = db.query(Submission).filter(Submission.exam_id == e.id).all()
        marked  = sum(1 for s in subs if s.status in ("marked","locked","returned","reviewed"))
        rows.append({
            "exam":    e,
            "total":   len(subs),
            "marked":  marked,
            "pending": len(subs) - marked,
        })
    return _r(request, "marking_overview.html", rows=rows)