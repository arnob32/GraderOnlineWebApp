# routes/department_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.department import Department
from app.models.student import Student

router = APIRouter(prefix="/departments", tags=["Departments"])


class DepartmentIn(BaseModel):
    name: str


@router.get("/")
def list_departments(db: Session = Depends(get_db)):
    return [{"id": d.id, "name": d.name}
            for d in db.query(Department).order_by(Department.name).all()]


@router.post("/add", status_code=201)
def add_department(payload: DepartmentIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    if db.query(Department).filter(Department.name == name).first():
        raise HTTPException(400, "Department already exists")
    dept = Department(name=name)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return {"id": dept.id, "name": dept.name}


@router.delete("/{dept_id}", status_code=204)
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(404, "Department not found")
    db.delete(dept)
    db.commit()


@router.get("/{department_id}/students")
def students_by_department(department_id: int, db: Session = Depends(get_db)):
    return db.query(Student).filter(
        Student.department_id == department_id).all()