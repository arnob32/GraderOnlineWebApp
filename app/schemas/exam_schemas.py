from pydantic import BaseModel
from typing import List, Optional, Any


class PageResult(BaseModel):
    page_number:     int
    filename:        str
    file_path:       str
    extracted_id:    Optional[str]   = None
    extracted_name:  Optional[str]   = None
    confidence:      float           = 0.0
    matched_student: Optional[Any]   = None
    submission_id:   Optional[int]   = None
    status:          str             = "failed"   
    needs_review:    bool            = True
    duplicate:       Optional[Any]   = None        
    error:           Optional[str]   = None


class ExamUploadResponse(BaseModel):
    success:             bool
    total_pages:         int         = 0
    processed:           int         = 0
    matched_students:    int         = 0
    unmatched_students:  int         = 0
    matched_codes:       List[str]   = []
    results:             List[PageResult] = []
    message:             str         = ""