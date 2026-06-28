import json
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from app.models.base import Base


class Annotation(Base):
    __tablename__ = "annotations"

    id            = Column(Integer, primary_key=True, index=True)
    file_name     = Column(String(500), nullable=False, index=True)
    teacher_id    = Column(Integer, nullable=True, index=True)
    page_number   = Column(Integer, default=1,   nullable=False)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True, index=True)
    data_json     = Column(Text, nullable=False, default="{}")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(),
                           onupdate=func.now())

    def parse_data(self):
        try:
            return json.loads(self.data_json or "{}")
        except Exception:
            return {}

    def to_summary(self):
        data = self.parse_data()
        return {
            "id":            self.id,
            "file_name":     self.file_name,
            "teacher_id":    self.teacher_id,
            "page_number":   self.page_number,
            "submission_id": self.submission_id,
            "stroke_count":  len(data.get("strokes",   [])),
            "stamp_count":   len(data.get("stamps",    [])),
            "comment_count": len(data.get("comments",  [])),
            "updated_at":    str(self.updated_at) if self.updated_at else None,
        }