# app/models/feedback_template.py
"""
Grading feedback templates.
A template belongs to a question (and optionally an exam or grader).
Style: 'add' (start at 0, add points) or 'subtract' (start at max, subtract).
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import Base


class FeedbackTemplate(Base):
    __tablename__ = "feedback_templates"

    id          = Column(Integer, primary_key=True, index=True)
    # Scope — at least one must be set
    exam_id     = Column(Integer, ForeignKey("exams.id"),    nullable=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=True, index=True)
    teacher_id  = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)

    # Template content
    label       = Column(String,  nullable=False)          # "Correct definition"
    points      = Column(Float,   nullable=False)          # +2 or -1
    style       = Column(String,  default="add")           # "add" | "subtract"
    description = Column(Text,    nullable=True)           # optional longer note
    sort_order  = Column(Integer, default=0)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    exam        = relationship("Exam",     foreign_keys=[exam_id])
    question    = relationship("Question", foreign_keys=[question_id])
    teacher     = relationship("Teacher",  foreign_keys=[teacher_id])

    def to_dict(self):
        return {
            "id":          self.id,
            "exam_id":     self.exam_id,
            "question_id": self.question_id,
            "teacher_id":  self.teacher_id,
            "label":       self.label,
            "points":      self.points,
            "style":       self.style,
            "description": self.description,
            "sort_order":  self.sort_order,
        }