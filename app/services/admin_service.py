# services/admin_service.py
# Admin business logic — departments, semesters, subjects, teachers

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.semester import Semester
from app.models.subject import Subject, subject_departments
from app.models.teacher import Teacher


CROSS_YEAR_SEMESTERS = {"winter", "autumn", "fall"}



def create_department(db: Session, name: str) -> Department:
    name = name.strip()
    if db.query(Department).filter(Department.name == name).first():
        raise HTTPException(400, "Department already exists")
    dept = Department(name=name)
    db.add(dept); db.commit(); db.refresh(dept)
    return dept

def delete_department(db: Session, dept_id: int) -> None:
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(404, "Department not found")
    db.delete(dept); db.commit()




def create_semester(db: Session, name: str, year_start: int, term: str) -> Semester:
    name     = name.strip()
    year_end = year_start + 1 if name.lower() in CROSS_YEAR_SEMESTERS else year_start
    sem = Semester(name=name, year_start=year_start, year_end=year_end, term=term.strip())
    db.add(sem); db.commit(); db.refresh(sem)
    return sem

def delete_semester(db: Session, sem_id: int) -> None:
    sem = db.query(Semester).filter(Semester.id == sem_id).first()
    if not sem:
        raise HTTPException(404, "Semester not found")
    db.delete(sem); db.commit()




def create_subject(
    db:             Session,
    name:           str,
    code:           str,
    department_id:  int | None,        
    semester_id:    int,
    is_elective:    bool = False,      
    department_ids: list[int] = None,  
) -> Subject:
    subj = Subject(
        name          = name.strip(),
        code          = code.strip().upper(),
        department_id = department_id,
        semester_id   = semester_id,
        is_elective   = is_elective,
    )
    db.add(subj)
    db.flush()  

 
    seen = set()
    for dept_id in (department_ids or []):
        if dept_id and dept_id not in seen:
            seen.add(dept_id)
            db.execute(
                subject_departments.insert().values(
                    subject_id=subj.id, department_id=dept_id
                )
            )

    db.commit()
    db.refresh(subj)
    return subj

def assign_teacher_to_subject(db: Session, subject_id: int, teacher_id: int) -> None:
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")
    subj.teacher_id = teacher_id or None
    db.commit()

def delete_subject(db: Session, subject_id: int) -> None:
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")
    db.delete(subj); db.commit()



def approve_teacher(db: Session, teacher_id: int) -> None:
    t = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not t:
        raise HTTPException(404, "Teacher not found")
    t.is_approved = True; db.commit()

def reject_teacher(db: Session, teacher_id: int) -> None:
    t = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not t:
        raise HTTPException(404, "Teacher not found")
    db.delete(t); db.commit()