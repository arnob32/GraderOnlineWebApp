# services/auth_service.py
# Login / signup logic

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.teacher import Teacher
from app.utils.security import hash_password, verify_password


def login(db: Session, role: str, email: str, password: str) -> dict:
    """Verify credentials. Returns user dict on success, raises HTTPException on failure."""
    if role not in ("student", "teacher"):
        raise HTTPException(400, "Invalid role")

    model = Student if role == "student" else Teacher
    user  = db.query(model).filter(model.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")

    return {"id": user.id, "role": role,
            "name": user.name, "email": user.email}


def signup_student(db: Session, first_name: str, last_name: str, email: str,
                   password: str, student_code: str, semester_id: int,
                   department_id: int) -> None:
    if db.query(Student).filter(Student.email == email).first():
        raise HTTPException(400, "That email is already registered.")
    if db.query(Student).filter(Student.student_code == student_code).first():
        raise HTTPException(400, "That student code is already in use.")
    db.add(Student(
        first_name=first_name, last_name=last_name, email=email,
        password_hash=hash_password(password), student_code=student_code,
        semester=semester_id, department_id=department_id,
    ))
    db.commit()


def signup_teacher(db: Session, first_name: str, last_name: str, email: str,
                   password: str, teacher_code: str, department_id: int) -> None:
    if db.query(Teacher).filter(Teacher.email == email).first():
        raise HTTPException(400, "That email is already registered.")
    if db.query(Teacher).filter(Teacher.teacher_code == teacher_code).first():
        raise HTTPException(400, "That teacher code is already in use.")
    db.add(Teacher(
        first_name=first_name, last_name=last_name, email=email,
        password_hash=hash_password(password), teacher_code=teacher_code,
        department_id=department_id,
    ))
    db.commit()