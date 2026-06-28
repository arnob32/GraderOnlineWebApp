from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Submission(Base):
    __tablename__ = "submissions"

    id         = Column(Integer, primary_key=True, index=True)
    exam_id    = Column(Integer, ForeignKey("exams.id"),     nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"),  nullable=True,  index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"),  nullable=True)
    file_path  = Column(String,  nullable=False)
    page_count = Column(Integer, default=1)
    status     = Column(String,  default="uploaded", nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    exam           = relationship("Exam",         back_populates="submissions")
    student        = relationship("Student",      back_populates="submissions")
    mark           = relationship("Mark",         back_populates="submission", uselist=False)
    question_marks = relationship("QuestionMark", back_populates="submission",
                                  cascade="all, delete-orphan",
                                  order_by="QuestionMark.question_number")

    def is_graded(self):
        return self.mark is not None and self.mark.status in (
            "marked", "pending_review", "reviewed", "locked", "returned")