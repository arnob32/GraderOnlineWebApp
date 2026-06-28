# services/student_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.mark import Mark
from app.models.submission import Submission

def get_student_results(db: Session, submission_id: int, student_id: int) -> dict:
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub: raise HTTPException(404, "Submission not found")
    if sub.student_id != student_id: raise HTTPException(403, "Not allowed")
    mark = db.query(Mark).filter(Mark.submission_id == submission_id).first()
    return {
        "submission_id": sub.id,
        "student_id":    sub.student_id,
        "status":        sub.status,
        "file_path":     sub.file_path,
        "mark":          mark.to_dict() if mark else None,
    }

def get_approved_students(db: Session, subject_id: int,
                          sel_sem=None, search: str = None) -> list:
    from app.models.student import Student
    try:
        from app.models.enrollment_models import SubjectEnrollment, EnrollmentStatus
        q = (db.query(Student)
             .join(SubjectEnrollment, SubjectEnrollment.student_id == Student.id)
             .filter(SubjectEnrollment.subject_id == subject_id,
                     SubjectEnrollment.status == EnrollmentStatus.approved))
        if sel_sem: q = q.filter(SubjectEnrollment.semester == sel_sem)
        students = q.order_by(Student.id).all()
    except ImportError:
        return []
    if search:
        term = search.strip().lower()
        students = [s for s in students
                    if term in (s.name or "").lower()
                    or term in (s.student_code or "").lower()]
    return students