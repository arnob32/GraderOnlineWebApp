from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class Mark(Base):
    __tablename__ = "marks"

    id            = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"),
                           nullable=False, unique=True, index=True)

    score        = Column(Float,     default=0.0)
    max_score    = Column(Float,     default=0.0)
    percentage   = Column(Float,     default=0.0)
    letter_grade = Column(String(4), default="")
    comments     = Column(Text,    nullable=True)
    internal_note = Column(Text,   nullable=True)

    status    = Column(String(30), default="uploaded", index=True)
    is_locked = Column(Boolean,    default=False)

    teacher_id  = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)

    marked_at   = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(),
                         onupdate=func.now())

    submission = relationship("Submission", back_populates="mark",
                              foreign_keys=[submission_id])

    def compute_percentage(self):
        if self.max_score and self.max_score > 0:
            return round((self.score / self.max_score) * 100, 2)
        return 0.0

    def to_dict(self):
        return {
            "id":            self.id,
            "submission_id": self.submission_id,
            "score":         self.score,
            "max_score":     self.max_score,
            "percentage":    self.percentage,
            "letter_grade":  self.letter_grade,
            "comments":      self.comments,
            "internal_note": self.internal_note,
            "status":        self.status,
            "is_locked":     self.is_locked,
            "teacher_id":    self.teacher_id,
            "reviewer_id":   self.reviewer_id,
            "marked_at":   str(self.marked_at)   if self.marked_at   else None,
            "reviewed_at": str(self.reviewed_at) if self.reviewed_at else None,
            "released_at": str(self.released_at) if self.released_at else None,
            "updated_at":  str(self.updated_at)  if self.updated_at  else None,
        }