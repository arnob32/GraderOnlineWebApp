from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from app.models.base import Base

subject_departments = Table(
    "subject_departments", Base.metadata,
    Column("subject_id",    Integer, ForeignKey("subjects.id"),    primary_key=True),
    Column("department_id", Integer, ForeignKey("departments.id"), primary_key=True),
    extend_existing=True,
)

subject_teachers = Table(
    "subject_teachers", Base.metadata,
    Column("subject_id", Integer, ForeignKey("subjects.id"),  primary_key=True),
    Column("teacher_id", Integer, ForeignKey("teachers.id"), primary_key=True),
    extend_existing=True,
)

teacher_departments = Table(
    "teacher_departments", Base.metadata,
    Column("teacher_id",    Integer, ForeignKey("teachers.id"),    primary_key=True),
    Column("department_id", Integer, ForeignKey("departments.id"), primary_key=True),
    extend_existing=True,
)


class Subject(Base):
    __tablename__ = "subjects"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String,  nullable=False)
    code        = Column(String,  nullable=False, unique=True)
    description = Column(Text,    nullable=True)
    credits     = Column(Integer, default=3,    nullable=False)
    is_elective = Column(Boolean, default=True, nullable=False)
    is_active   = Column(Boolean, default=True, nullable=False)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    semester_id   = Column(Integer, ForeignKey("semesters.id"),   nullable=True)
    teacher_id    = Column(Integer, ForeignKey("teachers.id"),    nullable=True)

    department = relationship("Department", back_populates="subjects",
                              foreign_keys=[department_id])
    semester   = relationship("Semester",   back_populates="subjects")
    teacher    = relationship("Teacher",    back_populates="subjects",
                              foreign_keys=[teacher_id])

    departments = relationship("Department", secondary=subject_departments,
                               back_populates="subjects_assigned")
    teachers    = relationship("Teacher",    secondary=subject_teachers,
                               back_populates="subjects_assigned")

    enrollments = relationship("SubjectEnrollment", back_populates="subject")