from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Department(Base):
    __tablename__ = "departments"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String,  nullable=False, unique=True)

    students = relationship("Student", back_populates="department")
    teachers = relationship("Teacher", back_populates="department")
    exams    = relationship("Exam",    back_populates="department")
    subjects = relationship("Subject", back_populates="department",
                            foreign_keys="Subject.department_id")

    assigned_teachers = relationship(
        "Teacher", secondary="teacher_departments",
        back_populates="assigned_departments", overlaps="teachers")

    subjects_assigned = relationship(
        "Subject", secondary="subject_departments",
        back_populates="departments", overlaps="subjects")