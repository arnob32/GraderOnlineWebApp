from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id            = Column(Integer, primary_key=True, index=True)
    first_name    = Column(String,  nullable=False)
    last_name     = Column(String,  nullable=False)
    email         = Column(String,  unique=True, nullable=False)
    teacher_code  = Column(String,  unique=True, nullable=False)
    password_hash = Column(String,  nullable=False)
    is_approved   = Column(Boolean, default=False, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))

    department = relationship("Department", back_populates="teachers")
    exams      = relationship("Exam",    back_populates="teacher")
    subjects   = relationship("Subject", back_populates="teacher",
                              foreign_keys="Subject.teacher_id")

    assigned_departments = relationship(
        "Department", secondary="teacher_departments",
        back_populates="assigned_teachers", overlaps="department")

    subjects_assigned = relationship(
        "Subject", secondary="subject_teachers",
        back_populates="teachers", overlaps="subjects")

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"