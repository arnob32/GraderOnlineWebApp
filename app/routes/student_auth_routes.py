# app/routes/student_auth_routes.py
"""
Student login / logout.
Students log in with their Mtknr (student_code) + password.
Default password = student_code (set at Excel import time).
"""
import hashlib
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.student import Student

router    = APIRouter(tags=["Student Auth"])
templates = Jinja2Templates(directory="app/templates")

def _signup_ctx(db):
    from app.models.department import Department
    from app.models.semester import Semester
    return {
        "departments": db.query(Department).order_by(Department.name).all(),
        "semesters":   db.query(Semester).order_by(Semester.year_start.desc()).all(),
    }


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


@router.get("/student/login", response_class=HTMLResponse)
def student_login_page(request: Request):
    if request.session.get("role") == "student":
        return RedirectResponse("/dashboard/student", 303)
    return templates.TemplateResponse("student_login.html", {
        "request": request,
        "error":   None,
    })


@router.post("/student/login", response_class=HTMLResponse)
def student_login(
    request:      Request,
    student_code: str = Form(...),
    password:     str = Form(...),
    db:           Session = Depends(get_db),
):
    student = db.query(Student).filter(
        Student.student_code == student_code.strip()
    ).first()

    if not student:
        return templates.TemplateResponse("student_login.html", {
            "request":      request,
            "error":        "Student number not found.",
            "student_code": student_code,
        })

    # Check password — sha256 hash comparison
    if student.password_hash != _hash(password):
        # Also try plain text match in case password was stored differently
        if student.password_hash != password:
            return templates.TemplateResponse("student_login.html", {
                "request":      request,
                "error":        "Incorrect password. Default password is your student number.",
                "student_code": student_code,
            })

    # Set session
    request.session["user_id"] = str(student.id)
    request.session["role"]    = "student"
    request.session["name"]    = f"{student.first_name} {student.last_name}"

    return RedirectResponse("/dashboard/student", status_code=303)


@router.get("/student/logout")
def student_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/student/login", status_code=303)
@router.get("/student/signup")
def student_signup_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("student_signup.html",
        {"request": request, **_signup_ctx(db)})

@router.post("/student/signup-form")
def student_signup(request: Request,
                   first_name: str = Form(...), last_name: str = Form(...),
                   email: str = Form(...), password: str = Form(...),
                   student_code: str = Form(...), semester_id: int = Form(...),
                   department_id: int = Form(...), db: Session = Depends(get_db)):
    ctx = _signup_ctx(db)
    try:
        from app.services.auth_service import signup_student
        signup_student(db, first_name, last_name, email, password,
                       student_code, semester_id, department_id)
    except Exception as e:
        return templates.TemplateResponse("student_signup.html",
            {"request": request, "error": str(e), **ctx})
    return templates.TemplateResponse("student_login.html",
        {"request": request, "success": "Account created! You can now sign in."})