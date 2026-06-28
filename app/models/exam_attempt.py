from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class ExamAttemptRecord(Base):
    __tablename__ = "exam_attempt_records"

    id             = Column(Integer, primary_key=True, index=True)
    student_id     = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    exam_id        = Column(Integer, ForeignKey("exams.id"),    nullable=True,  index=True)
    subject_id     = Column(Integer, ForeignKey("subjects.id"), nullable=True,  index=True)
    attempt_number = Column(Integer, default=1,       nullable=False)
    status         = Column(String(30), default="active")
    attempted_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    student = relationship("Student", foreign_keys=[student_id],
                           back_populates="exam_attempts")
    exam    = relationship("Exam",    foreign_keys=[exam_id],
                           back_populates="attempts")

    def to_dict(self):
        return {
            "id":             self.id,
            "student_id":     self.student_id,
            "exam_id":        self.exam_id,
            "subject_id":     self.subject_id,
            "attempt_number": self.attempt_number,
            "status":         self.status,
            "attempted_at":   self.attempted_at.isoformat() if self.attempted_at else None,
        }