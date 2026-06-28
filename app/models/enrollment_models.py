import enum
from datetime import datetime, timezone
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        String, UniqueConstraint, Enum as SAEnum)
from sqlalchemy.orm import relationship
from app.models.base import Base


class EnrollmentStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


class SubjectEnrollment(Base):
    __tablename__ = "subject_enrollments"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", "semester",
                                       name="uq_enrollment"),)

    id           = Column(Integer, primary_key=True, index=True)
    student_id   = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id   = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    semester     = Column(Integer, nullable=False)
    status       = Column(SAEnum(EnrollmentStatus), default=EnrollmentStatus.pending,
                          nullable=False)
    is_elective  = Column(Boolean, default=True, nullable=False)
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at  = Column(DateTime, nullable=True)
    reviewed_by  = Column(Integer,  nullable=True)
    notes        = Column(String,   nullable=True)

    student = relationship("Student", back_populates="enrollments")
    subject = relationship("Subject", back_populates="enrollments")


class RetakeStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


class RetakeRequest(Base):
    __tablename__ = "retake_requests"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", "attempt_number",
                                       name="uq_retake"),)

    id             = Column(Integer, primary_key=True, index=True)
    student_id     = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id     = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    enrollment_id  = Column(Integer, ForeignKey("subject_enrollments.id"), nullable=True)
    attempt_number = Column(Integer, nullable=False)
    status         = Column(SAEnum(RetakeStatus), default=RetakeStatus.pending,
                            nullable=False)
    requested_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at    = Column(DateTime, nullable=True)
    reviewed_by    = Column(Integer,  nullable=True)
    notes          = Column(String,   nullable=True)

    student    = relationship("Student")
    subject    = relationship("Subject")
    enrollment = relationship("SubjectEnrollment")