# routes/exam_upload.py
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.exam import Exam
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.submission import Submission
from app.services.exam_upload_service import (
    process_upload, generate_student_pdf,
    advance_pipeline, UPLOADED_PAPERS_DIR,
)

def _student_name(s) -> str:
    try:
        if hasattr(s, "first_name") and s.first_name:
            return f"{s.first_name} {s.last_name or ''}".strip()
        raw = getattr(s, "name", None)
        if raw and not callable(raw):
            return str(raw)
    except Exception:
        pass
    return f"Student #{s.id}"
from app.schemas.exam_schemas import ExamUploadResponse

router      = APIRouter(prefix="/api/exams", tags=["Exam Upload"])
page_router = APIRouter(tags=["Exam Pages"])
templates   = Jinja2Templates(directory="app/templates")

Path("uploaded_exams").mkdir(exist_ok=True)
Path("generated_pdfs").mkdir(exist_ok=True)
Path("uploaded_papers").mkdir(exist_ok=True)
Path("outputs/crops").mkdir(parents=True, exist_ok=True)


@page_router.get("/exam-ocr/upload", response_class=HTMLResponse)
async def exam_ocr_upload_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("exam_ocr_upload.html", {
        "request":   request,
        "exams":     db.query(Exam).order_by(Exam.title).all(),
        "semesters": db.query(Semester).order_by(Semester.year_start.desc()).all(),
        "subjects":  db.query(Subject).order_by(Subject.name).all(),
    })


@router.get("/{exam_id}/students")
async def get_exam_students(exam_id: int, db: Session = Depends(get_db)):
    """Return all students with their submission status for this exam."""
    from app.models.student import Student

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")

    # Load ALL students — filter by department only if exam has one
    try:
        if getattr(exam, "department_id", None):
            students = db.query(Student).filter(
                Student.department_id == exam.department_id).all()
            if not students:
                students = db.query(Student).all()
        else:
            students = db.query(Student).all()

        # Sort by name safely
        try:
            students = sorted(students, key=lambda s: _student_name(s).lower())
        except Exception:
            pass
    except Exception:
        students = db.query(Student).all()

    # Get existing submissions for this exam
    existing = {
        s.student_id: s
        for s in db.query(Submission).filter(Submission.exam_id == exam_id).all()
    }

    result = []
    for s in students:
        sub = existing.get(s.id)
        result.append({
            "id":            s.id,
            "name":          _student_name(s),
            "student_code":  getattr(s, "student_code", None) or str(s.id),
            "submitted":     s.id in existing,
            "status":        sub.status if sub else None,
            "submission_id": sub.id     if sub else None,
        })

    return {"exam_id": exam_id, "students": result, "total": len(result)}


@router.get("/scanner/status")
async def scanner_status():
    try:
        from app.services.exam_upload_service import _extract_fn, _scan_fn
        return {"model_loaded": bool(_extract_fn or _scan_fn)}
    except Exception:
        return {"model_loaded": False}


@router.post("/upload")
async def upload_exam_papers(
    exam_id:   str = Form(...),
    exam_name: str = Form(""),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    try:
        result = await process_upload(exam_id, files, db)
        return ExamUploadResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "success": False, "total_pages": 0, "processed": 0,
            "matched_students": 0, "unmatched_students": 0,
            "matched_codes": [], "results": [],
            "message": f"Server error: {e}",
        })


class AssignPageRequest(BaseModel):
    exam_id:    str
    student_id: int
    page_file:  str


@router.post("/assign-page")
async def assign_page(req: AssignPageRequest, db: Session = Depends(get_db)):
    from app.models.student import Student
    exam    = db.query(Exam).filter(Exam.id == int(req.exam_id)).first()
    student = db.query(Student).filter(Student.id == req.student_id).first()
    if not exam:    raise HTTPException(404, "Exam not found")
    if not student: raise HTTPException(404, "Student not found")
    if not Path(req.page_file).exists():
        raise HTTPException(404, "Page file not found on disk")

    existing = db.query(Submission).filter(
        Submission.exam_id    == int(req.exam_id),
        Submission.student_id == req.student_id,
        Submission.status     != "duplicate",
    ).first()
    if existing:
        raise HTTPException(409, f"Student already has submission id={existing.id}")

    sub_kw = {
        "exam_id":   int(req.exam_id),
        "student_id": req.student_id,
        "file_path":  req.page_file,
        "status":     "assigned",
    }
    if hasattr(Submission, "page_count"):
        sub_kw["page_count"] = 1
    sub = Submission(**sub_kw)
    db.add(sub); db.commit(); db.refresh(sub)

    return {
        "ok":            True,
        "submission_id": sub.id,
        "student_id":    student.id,
        "student_code":  getattr(student, "student_code", str(student.id)),
        "student_name":  _student_name(student),
        "status":        sub.status,
    }


@router.post("/{submission_id}/advance-status")
async def advance_status(submission_id: int, db: Session = Depends(get_db)):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub: raise HTTPException(404, "Submission not found")
    sub.status = advance_pipeline(sub.status)
    db.commit()
    return {"ok": True, "submission_id": sub.id, "status": sub.status}


class DuplicateRequest(BaseModel):
    keep_submission_id: int


@router.post("/{submission_id}/mark-duplicate")
async def mark_duplicate(submission_id: int, req: DuplicateRequest,
                          db: Session = Depends(get_db)):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub: raise HTTPException(404, "Submission not found")
    sub.status = "duplicate"
    if hasattr(sub, "duplicate_of"):
        sub.duplicate_of = req.keep_submission_id
    db.commit()
    return {"ok": True, "submission_id": sub.id,
            "duplicate_of": req.keep_submission_id}


class GeneratePdfRequest(BaseModel):
    exam_id:      str
    student_id:   str
    student_name: Optional[str] = ""
    file_paths:   List[str]


@router.post("/generate-pdf")
async def generate_pdf(req: GeneratePdfRequest, db: Session = Depends(get_db)):
    return await generate_student_pdf(
        req.exam_id, req.student_id,
        req.student_name or "", req.file_paths, db,
    )


@router.get("/pdf/{exam_id}/{filename}")
async def download_student_pdf(exam_id: str, filename: str):
    pdf_path = UPLOADED_PAPERS_DIR / exam_id / filename
    if not pdf_path.exists():
        raise HTTPException(404, f"PDF not found: {filename}")
    return FileResponse(str(pdf_path), media_type="application/pdf",
                        filename=f"{exam_id}_{filename}")