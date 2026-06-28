# schemas/exam.py
from typing import Optional
from pydantic import BaseModel


class ExamCreatePayload(BaseModel):
    title:         str
    subject_id:    Optional[int] = None
    department_id: Optional[int] = None
    semester:      Optional[int] = None
    total_marks:   int
    teacher_id:    int