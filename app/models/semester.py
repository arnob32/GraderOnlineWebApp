from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Semester(Base):
    __tablename__ = "semesters"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String,  nullable=False)
    year_start = Column(Integer, nullable=False)
    year_end   = Column(Integer, nullable=False)
    term       = Column(String,  nullable=False)

    subjects = relationship("Subject", back_populates="semester")

    @property
    def label(self):
        return f"{self.name} {self.year_start}/{self.year_end} ({self.term})"

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "year_start": self.year_start,
            "year_end":   self.year_end,
            "term":       self.term,
            "label":      self.label,
        }