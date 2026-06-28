from sqlalchemy import Column, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import relationship
from app.models.base import Base

class Question(Base):
    __tablename__ = "questions"

    id              = Column(Integer, primary_key=True, index=True)
    exam_id         = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    question_number = Column(Integer, nullable=False)
    text            = Column(Text,    nullable=False)
    answer_type     = Column(String(50), nullable=True)
    max_marks       = Column(Integer, nullable=False, default=0)

    # Answer box coordinates saved during PDF generation (PDF points, A4)
    # x, y = top-left corner of box in PDF coordinate space (y from bottom)
    # w, h = width and height
    # page = page number (1-based)
    box_x    = Column(Float, nullable=True)
    box_y    = Column(Float, nullable=True)
    box_w    = Column(Float, nullable=True)
    box_h    = Column(Float, nullable=True)
    box_page = Column(Integer, nullable=True)

    exam           = relationship("Exam",         back_populates="questions")
    question_marks = relationship("QuestionMark", back_populates="question",
                                  cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":              self.id,
            "exam_id":         self.exam_id,
            "question_number": self.question_number,
            "text":            self.text,
            "answer_type":     self.answer_type,
            "max_marks":       self.max_marks,
            "box_x":           self.box_x,
            "box_y":           self.box_y,
            "box_w":           self.box_w,
            "box_h":           self.box_h,
            "box_page":        self.box_page,
        }