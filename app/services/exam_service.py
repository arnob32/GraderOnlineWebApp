# services/exam_service.py
import os
import uuid
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.exam import Exam
from app.models.question import Question
from app.models.subject import Subject
from app.models.student import Student
from app.models.exam_attempt import ExamAttemptRecord
from app.utils import pdf_generator


def resolve_subject_and_code(db: Session, subject_str: str, course_code: str):
    resolved_code = course_code.strip() if course_code else ""
    if not resolved_code and subject_str and subject_str.strip():
        try:
            subj = db.query(Subject).filter(Subject.id == int(subject_str.strip())).first()
            if subj and subj.code:
                resolved_code = subj.code.strip()
        except (ValueError, TypeError):
            pass
    return resolved_code


def create_exam_record(db: Session, title: str, resolved_code: str,
                       description: str, department_id: int, semester: int,
                       total_marks: int, teacher_id: int,
                       cover_rules: str, exam_date: str, exam_time: str) -> Exam:
    exam = Exam(
        title         = title.strip(),
        department_id = department_id if department_id > 0 else None,
        semester      = semester      if semester      > 0 else None,
        total_marks   = total_marks,
        teacher_id    = teacher_id,
    )
    for field, val in [
        ("course_code", resolved_code),
        ("description", description.strip() if description else ""),
        ("cover_rules", cover_rules.strip() if cover_rules else ""),
        ("exam_date",   exam_date),
        ("exam_time",   exam_time),
    ]:
        if hasattr(exam, field):
            setattr(exam, field, val)
    try:
        db.add(exam); db.commit(); db.refresh(exam)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create exam: {e}")
    return exam


def link_subject(db: Session, exam: Exam, subject_str: str,
                 resolved_code: str) -> int | None:
    subject_id = None
    if subject_str and subject_str.strip():
        try:
            sid  = int(subject_str.strip())
            subj = db.query(Subject).filter(Subject.id == sid).first()
            if subj:
                subject_id = subj.id
                if hasattr(exam, "subject_id"):
                    exam.subject_id = subject_id
                db.commit()
        except (ValueError, TypeError):
            pass
    if not subject_id and resolved_code:
        subj = db.query(Subject).filter(Subject.code == resolved_code).first()
        if subj and hasattr(exam, "subject_id"):
            subject_id = exam.subject_id = subj.id
            db.commit()
    return subject_id


def save_questions(db: Session, exam_id: int, questions: list) -> None:
    for i, q in enumerate(questions, start=1):
        # Read answer_type from either key the JS might send
        answer_type = str(
            q.get("answer_type") or q.get("type") or "small"
        ).strip()
        row = Question(
            exam_id         = exam_id,
            question_number = i,
            text            = str(q.get("text", "")).strip(),
            max_marks       = int(q.get("marks", 0)) if str(q.get("marks","")).isdigit() else 0,
            answer_type     = answer_type,
        )
        for field, key in [("mcq_options","options"),("correct_answer","correct_answer")]:
            if hasattr(row, field) and q.get(key):
                setattr(row, field, str(q[key]).strip())
        db.add(row)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to save questions: {e}")


async def save_question_images(db: Session, form, exam_id: int,
                               questions: list) -> dict:
    question_image_paths = {}
    for i, _q in enumerate(questions, start=1):
        uploaded = form.get(f"question_image_{i}")
        if not uploaded or not getattr(uploaded, "filename", None):
            continue
        ext = os.path.splitext(uploaded.filename)[1].lower() or ".png"
        if ext not in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
            raise HTTPException(400, f"Unsupported image for question {i}")
        name      = f"exam_{exam_id}_q{i}_{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(pdf_generator.TEMP_IMAGE_DIR, name)
        with open(save_path, "wb") as f:
            f.write(await uploaded.read())
        question_image_paths[i] = save_path
        db_q = db.query(Question).filter(
            Question.exam_id == exam_id,
            Question.question_number == i).first()
        if db_q and hasattr(db_q, "image_path"):
            db_q.image_path = save_path
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to save question images: {e}")
    return question_image_paths


def _student_name(s) -> str:
    if hasattr(s, "first_name") and s.first_name:
        return f"{s.first_name} {s.last_name or ''}".strip()
    if hasattr(s, "name") and isinstance(s.name, str):
        return s.name
    return str(s.id)


def get_eligible_students(db: Session, subject_id: int | None,
                          semester: int) -> list[tuple]:
    seen: set     = set()
    entries: list = []

    if subject_id:
        try:
            from app.models.enrollment_models import (
                SubjectEnrollment, EnrollmentStatus,
                RetakeRequest, RetakeStatus,
            )
            enrolled = db.query(SubjectEnrollment).filter(
                SubjectEnrollment.subject_id == subject_id,
                SubjectEnrollment.status     == EnrollmentStatus.approved,
            ).all()
            for e in enrolled:
                if not e.student:
                    student = db.query(Student).filter(
                        Student.id == e.student_id).first()
                else:
                    student = e.student
                if student and student.id not in seen:
                    entries.append((student, 1))
                    seen.add(student.id)
            for r in db.query(RetakeRequest).filter(
                RetakeRequest.subject_id == subject_id,
                RetakeRequest.status     == RetakeStatus.approved,
            ).all():
                if r.student and r.student_id not in seen:
                    entries.append((r.student, r.attempt_number))
                    seen.add(r.student_id)
        except ImportError:
            pass

    if not entries:
        subj    = db.query(Subject).filter(Subject.id == subject_id).first() if subject_id else None
        dept_id = getattr(subj, "department_id", None) if subj else None
        q       = db.query(Student)
        if dept_id:
            q = q.filter(Student.department_id == dept_id)
        for student in q.all():
            if student.id not in seen:
                entries.append((student, 1))
                seen.add(student.id)

    if not entries:
        for student in db.query(Student).all():
            if student.id not in seen:
                entries.append((student, 1))
                seen.add(student.id)

    entries.sort(key=lambda x: _student_name(x[0]).lower())
    print(f"[EXAM] Eligible students for subject={subject_id}: "
          f"{[_student_name(s) for s, _ in entries]}")
    return entries


def generate_pdfs(db: Session, exam: Exam, students_entries: list,
                  questions: list, question_image_paths: dict,
                  reference_boxes: list, subject_id: int | None) -> list:
    generated = []

    # Fetch DB question objects once — used to save box coordinates
    db_question_objs = (
        db.query(Question)
        .filter(Question.exam_id == exam.id)
        .order_by(Question.question_number)
        .all()
    )

    for student, attempt_num in students_entries:
        db.add(ExamAttemptRecord(
            student_id     = student.id,
            exam_id        = exam.id,
            subject_id     = subject_id or 0,
            attempt_number = attempt_num,
            status         = "active",
        ))
        if attempt_num > 1 and subject_id:
            try:
                from app.models.enrollment_models import RetakeRequest, RetakeStatus
                consumed = db.query(RetakeRequest).filter(
                    RetakeRequest.student_id     == student.id,
                    RetakeRequest.subject_id     == subject_id,
                    RetakeRequest.attempt_number == attempt_num,
                    RetakeRequest.status         == RetakeStatus.approved,
                ).first()
                if consumed:
                    db.delete(consumed)
            except ImportError:
                pass

        try:
            filename = pdf_generator.generate_exam_pdf(
                exam=exam,
                student=student,
                questions=questions,
                question_image_paths=question_image_paths,
                reference_boxes=reference_boxes,
                db=db,
                db_questions=db_question_objs,
            )
            if filename:
                generated.append(filename)
        except Exception as e:
            print(f"[ERROR] PDF failed for student {student.id}: {e}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[WARN] Failed to record attempts: {e}")
    return generated