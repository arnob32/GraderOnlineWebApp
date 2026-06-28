from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.models.base import Base


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id        = Column(Integer, primary_key=True, index=True)
    exam_id   = Column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    sent_by   = Column(Integer, nullable=True)
    recipient = Column(String(255), nullable=False)
    status    = Column(String(50),  nullable=False, default="pending")
    message   = Column(Text,        nullable=True)
    sent_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))