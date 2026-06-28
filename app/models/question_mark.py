from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class QuestionMark(Base):
    __tablename__ = "question_marks"

    id              = Column(Integer, primary_key=True, index=True)
    submission_id   = Column(Integer, ForeignKey("submissions.id"),
                             nullable=False, index=True)
    question_id     = Column(Integer, ForeignKey("questions.id"),
                             nullable=False, index=True)
    question_number = Column(Integer, nullable=False)

    awarded_marks  = Column(Float,   default=0.0)
    max_marks      = Column(Float,   default=0.0)
    comment        = Column(Text,    nullable=True)
    is_auto_marked = Column(Boolean, default=False)
    review_status  = Column(String(20), default="pending")
    marked_by      = Column(Integer, nullable=True)
    reviewed_by    = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())

    submission = relationship("Submission", back_populates="question_marks",
                              foreign_keys=[submission_id])
    question   = relationship("Question",   back_populates="question_marks",
                              foreign_keys=[question_id])

    def to_dict(self):
        return {
            "id":              self.id,
            "submission_id":   self.submission_id,
            "question_id":     self.question_id,
            "question_number": self.question_number,
            "awarded_marks":   self.awarded_marks,
            "max_marks":       self.max_marks,
            "comment":         self.comment,
            "review_status":   self.review_status,
        }