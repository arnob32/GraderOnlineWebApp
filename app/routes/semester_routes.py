# routes/semester_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.semester import Semester
from app.services.admin_service import create_semester, delete_semester

router = APIRouter(prefix="/semesters", tags=["Semesters"])


class SemesterIn(BaseModel):
    name:       str
    year_start: int
    term:       str


@router.get("/")
def list_semesters(db: Session = Depends(get_db)):
    return [s.to_dict() for s in
            db.query(Semester).order_by(Semester.year_start.desc()).all()]


@router.post("/add", status_code=201)
def add_semester(payload: SemesterIn, db: Session = Depends(get_db)):
    exists = db.query(Semester).filter(
        Semester.name       == payload.name.strip(),
        Semester.year_start == payload.year_start,
        Semester.term       == payload.term.strip(),
    ).first()
    if exists:
        raise HTTPException(400, "Semester already exists.")
    sem = create_semester(db, payload.name, payload.year_start, payload.term)
    return sem.to_dict()


@router.delete("/{semester_id}", status_code=204)
def remove_semester(semester_id: int, db: Session = Depends(get_db)):
    delete_semester(db, semester_id)