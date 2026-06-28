from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.department import Department
from app.models.semester import Semester
from app.models.student import Student
from app.models.teacher import Teacher
from app.utils.security import hash_password, verify_password

router    = APIRouter(tags=["Auth"])
templates = Jinja2Templates(directory="app/templates")

def _signup_ctx(db):
    return {
        "departments": db.query(Department).order_by(Department.name).all(),
        "semesters":   db.query(Semester).order_by(Semester.year_start.desc(), Semester.id).all(),
    }

def _render_teacher_login(request, error="", success="", **kw):
    return templates.TemplateResponse("teacher_login.html",
        {"request": request, "error": error, "success": success, **kw})

def _render_teacher_signup(request, db, error="", **kw):
    return templates.TemplateResponse("teacher_signup.html",
        {"request": request, "error": error,
         "departments": db.query(Department).order_by(Department.name).all(), **kw})

# ── Auth pages ────────────────────────────────────────────────────────────────

@router.get("/")
def auth_page(request: Request):
    return RedirectResponse("/auth/login", status_code=303)

@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("teacher_login.html", {"request": request})

@router.get("/signup")
def signup_page(request: Request, db: Session = Depends(get_db)):
    return _render_teacher_signup(request, db)

# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login")
def login_user(request: Request, role: str = Form("teacher"),
               email: str = Form(...), password: str = Form(...),
               db: Session = Depends(get_db)):
    user = db.query(Teacher).filter(Teacher.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return _render_teacher_login(request,
            error="Incorrect email or password.", prefill_email=email)
    if not getattr(user, "is_approved", True):
        return _render_teacher_login(request,
            error="Your account is pending admin approval.", prefill_email=email)
    request.session["user_id"] = user.id
    request.session["role"]    = "teacher"
    return RedirectResponse(url="/dashboard/teacher", status_code=303)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)

@router.get("/me")
def get_me(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/auth/login", status_code=303)
    return {"id": request.session["user_id"], "role": request.session.get("role")}

# ── Student signup (kept for student portal) ──────────────────────────────────

@router.post("/student/signup")
def student_signup(request: Request,
                   first_name: str = Form(...), last_name: str = Form(...),
                   email: str = Form(...), password: str = Form(...),
                   student_code: str = Form(...), semester_id: int = Form(...),
                   department_id: int = Form(...), db: Session = Depends(get_db)):
    if db.query(Student).filter(Student.email == email).first():
        return templates.TemplateResponse("student_signup.html",
            {"request": request, "error": "That email is already registered.",
             **_signup_ctx(db)})
    if db.query(Student).filter(Student.student_code == student_code).first():
        return templates.TemplateResponse("student_signup.html",
            {"request": request, "error": "That student code is already in use.",
             **_signup_ctx(db)})
    db.add(Student(first_name=first_name, last_name=last_name, email=email,
                   password_hash=hash_password(password), student_code=student_code,
                   semester=semester_id, department_id=department_id))
    db.commit()
    return templates.TemplateResponse("student_login.html",
        {"request": request, "success": "Account created! You can now sign in."})

# ── Teacher signup ────────────────────────────────────────────────────────────

@router.post("/teacher/signup")
def teacher_signup(request: Request,
                   first_name: str = Form(...), last_name: str = Form(...),
                   email: str = Form(...), password: str = Form(...),
                   teacher_code: str = Form(...),
                   position: str = Form(""),        # accepted but ignored
                   department_id: int = Form(...), db: Session = Depends(get_db)):
    if db.query(Teacher).filter(Teacher.email == email).first():
        return _render_teacher_signup(request, db,
            error="That email is already registered.")
    if db.query(Teacher).filter(Teacher.teacher_code == teacher_code).first():
        return _render_teacher_signup(request, db,
            error="That teacher code is already in use.")
    # Build teacher without 'position' — not in model
    teacher = Teacher(
        first_name    = first_name,
        last_name     = last_name,
        email         = email,
        password_hash = hash_password(password),
        teacher_code  = teacher_code,
        department_id = department_id,
    )
    db.add(teacher)
    db.commit()
    return _render_teacher_login(request,
        success="Account created! Await admin approval before signing in.")