# services/submission_service.py

from typing import Optional
from sqlalchemy.orm import Session

from app.models.mark import Mark
from app.models.submission import Submission


def get_student_directory(db: Session, teacher_id, subject_id: Optional[int],
                           exam_id: Optional[int], status: Optional[str]) -> dict:
    from app.models.exam import Exam
    from app.models.student import Student
    from app.models.subject import Subject
    from app.models.department import Department
    Semester = None
    try:
        from app.models.semester import Semester
    except ImportError:
        pass

    q = (db.query(Submission, Mark, Exam)
         .outerjoin(Mark, Mark.submission_id == Submission.id)
         .join(Exam, Exam.id == Submission.exam_id))

    if teacher_id:
        from sqlalchemy import or_
        q = q.filter(or_(Exam.teacher_id == int(teacher_id),
                         Exam.teacher_id.is_(None)))

    q = q.filter(Submission.status.in_(
        [status] if status else
        ["marked", "returned", "locked", "reviewed",
         "pending_review", "sent_for_marking", "uploaded"]
    ))
    if exam_id:
        q = q.filter(Submission.exam_id == exam_id)

    rows = q.order_by(Submission.id.desc()).all()
    if not rows:
        return {"total": 0, "results": []}

    # Bulk fetch related objects
    exam_subject_ids = {e.subject_id for _, _, e in rows if e and e.subject_id}
    subjects_map = {s.id: s for s in db.query(Subject)
                    .filter(Subject.id.in_(exam_subject_ids)).all()} if exam_subject_ids else {}

    sem_ids  = {s.semester_id for s in subjects_map.values() if s.semester_id}
    sems_map = {s.id: s for s in db.query(Semester)
                .filter(Semester.id.in_(sem_ids)).all()} if (sem_ids and Semester) else {}

    stu_ids      = {sub.student_id for sub, _, _ in rows if sub.student_id}
    students_map = {s.id: s for s in db.query(Student)
                    .filter(Student.id.in_(stu_ids)).all()} if stu_ids else {}

    # Bulk fetch departments
    dept_ids  = {s.department_id for s in students_map.values() if getattr(s,"department_id",None)}
    depts_map = {d.id: d for d in db.query(Department)
                 .filter(Department.id.in_(dept_ids)).all()} if dept_ids else {}

    results = []
    for sub, mark, exam in rows:
        if subject_id and exam and getattr(exam, "subject_id", None) != subject_id:
            continue

        student = students_map.get(sub.student_id)
        subj    = subjects_map.get(exam.subject_id) if (exam and exam.subject_id) else None
        sem     = sems_map.get(subj.semester_id)    if (subj and subj.semester_id) else None
        dept    = depts_map.get(getattr(student, "department_id", None)) if student else None

        # Semester label
        if sem:
            sem_label = (getattr(sem, "label", None) or
                         f"{getattr(sem,'name','')} {getattr(sem,'year_start','')}".strip() or
                         f"Sem {sem.id}")
            sem_id = sem.id
        elif exam and getattr(exam, "semester", None):
            sem_label = f"Semester {exam.semester}"
            sem_id    = exam.semester
        else:
            sem_label = "—"
            sem_id    = None

        dept_name = getattr(dept, "name", "") if dept else ""
        dept_id   = getattr(dept, "id",   None) if dept else None

        results.append({
            "submission_id":   sub.id,
            "student_id":      sub.student_id,
            "student_name":    student.name if student else f"Student #{sub.student_id}",
            "student_code":    getattr(student, "student_code", "") or "",
            "student_email":   getattr(student, "email", "") or "",
            "department_name": dept_name,
            "department_id":   dept_id,
            "semester":        sem_label,
            "semester_id":     sem_id,
            "exam_id":         sub.exam_id,
            "exam_title":      (exam.title if exam else f"Exam #{sub.exam_id}") or "",
            "subject_name":    getattr(subj, "name", "") or "",
            "subject_code":    getattr(subj, "code", "") or "",
            "subject_id":      getattr(subj, "id",   None) if subj else None,
            "exam_semester":   sem_label,
            "status":          sub.status or "uploaded",
            "score":           mark.score        if mark else None,
            "max_score":       mark.max_score    if mark else None,
            "percentage":      mark.percentage   if mark else None,
            "letter_grade":    (mark.letter_grade if mark else "") or "",
            "sent_to_student": sub.status == "returned",
            "file_url":        f"/uploads/download-annotated-pdf/{sub.id}" if sub.file_path else "",
            "marked_at":       mark.marked_at.isoformat()   if (mark and mark.marked_at)   else None,
            "released_at":     mark.released_at.isoformat() if (mark and mark.released_at) else None,
        })
    return {"total": len(results), "results": results}