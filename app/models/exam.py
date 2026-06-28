from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Exam(Base):
    __tablename__ = "exams"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String,  nullable=False)
    semester    = Column(Integer, nullable=True)
    total_marks = Column(Integer, nullable=True)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    teacher_id    = Column(Integer, ForeignKey("teachers.id"),    nullable=True)
    subject_id    = Column(Integer, ForeignKey("subjects.id"),    nullable=True)

    department  = relationship("Department",        back_populates="exams")
    teacher     = relationship("Teacher",           back_populates="exams")
    submissions = relationship("Submission",        back_populates="exam")
    questions   = relationship("Question",          back_populates="exam",
                               cascade="all, delete-orphan",
                               order_by="Question.question_number")
    subject     = relationship("Subject")
    attempts    = relationship("ExamAttemptRecord", back_populates="exam")