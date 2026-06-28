from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Student(Base):
    __tablename__ = "students"

    id            = Column(Integer, primary_key=True, index=True)
    first_name    = Column(String,  nullable=False)
    last_name     = Column(String,  nullable=False)
    email         = Column(String,  unique=True, nullable=False)
    student_code  = Column(String,  unique=True, nullable=False)
    semester      = Column(Integer, nullable=False)
    password_hash = Column(String,  nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))

    department    = relationship("Department", back_populates="students")
    submissions   = relationship("Submission", back_populates="student",
                                 cascade="all, delete-orphan")
    enrollments   = relationship("SubjectEnrollment", back_populates="student")
    exam_attempts = relationship("ExamAttemptRecord",  back_populates="student")

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {
            "id":            self.id,
            "first_name":    self.first_name,
            "last_name":     self.last_name,
            "name":          self.name,
            "email":         self.email,
            "student_code":  self.student_code,
            "semester":      self.semester,
            "department_id": self.department_id,
        }