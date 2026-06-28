# schemas/annotation.py
from typing import Optional
from pydantic import BaseModel, Field


class AnnotationData(BaseModel):
    strokes:    list[dict] = Field(default_factory=list)
    highlights: list[dict] = Field(default_factory=list)
    comments:   list[dict] = Field(default_factory=list)
    stamps:     list[dict] = Field(default_factory=list)
    markBoxes:  list[dict] = Field(default_factory=list)


class AnnotationPayload(BaseModel):
    file_name:     str
    submission_id: Optional[int] = None
    teacher_id:    Optional[int] = None
    page_number:   int = 1
    data:          AnnotationData