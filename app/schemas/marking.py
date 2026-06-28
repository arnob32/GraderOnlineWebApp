# schemas/marking.py
from typing import List, Optional
from pydantic import BaseModel, Field

class QuestionMarkIn(BaseModel):
    question_id:     int
    question_number: Optional[int] = None   # optional - may be null in DB
    awarded_marks:   float = Field(..., ge=0)
    max_marks:       float = Field(..., ge=0)
    comment:         Optional[str] = ""

class SaveMarksPayload(BaseModel):
    teacher_id:     Optional[int] = None
    feedback:       Optional[str] = ""
    status:         Optional[str] = "marked"
    letter_grade:   Optional[str] = ""
    question_marks: List[QuestionMarkIn]

class LockPayload(BaseModel):
    admin_id:      Optional[int] = None
    internal_note: Optional[str] = ""

class AdjustMarkPayload(BaseModel):
    teacher_id: Optional[int] = None
    delta:      float
    reason:     Optional[str] = ""

class BulkReleasePayload(BaseModel):
    submission_ids: List[int]

class SendDirectoryPayload(BaseModel):
    submission_ids: List[int]
    subject_id:     Optional[int] = None
    message:        Optional[str] = ""

class SendToAdminPayload(BaseModel):
    exam_id: int
    note:    Optional[str] = ""

class ResolveRemarkPayload(BaseModel):
    resolved_by: Optional[int] = None
    decision:    str
    resolution:  Optional[str] = ""