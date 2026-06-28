# routes/uploaded_exams_routes.py
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.mark import Mark
from app.models.submission import Submission

router    = APIRouter(tags=["Uploaded Exams"])
templates = Jinja2Templates(directory="app/templates")
NO_CACHE  = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache", "Expires": "0",
}

# Statuses that belong on Uploaded Papers page (ungraded only)
UNGRADED_STATUSES = {"uploaded", "assigned", "sent_for_marking"}

def _find_file(filename: str):
    safe = Path(filename).name
    matches = []
    for d in ["uploaded_papers", "uploaded_exams", "uploads", "Uploads"]:
        for root, _, files in os.walk(d):
            if safe in files:
                p = Path(root) / safe
                matches.append(p)
    if not matches: return None
    return max(matches, key=lambda p: p.stat().st_size)


@router.get("/uploads/uploaded-exams", response_class=HTMLResponse)
def uploaded_exams_page(request: Request, db: Session = Depends(get_db)):
    uid      = request.session.get("user_id")
    is_admin = request.session.get("is_admin")
    if not uid and not is_admin:
        return RedirectResponse("/auth/login", status_code=303)
    teacher = None
    if uid:
        try:
            from app.models.teacher import Teacher
            teacher = db.query(Teacher).filter(Teacher.id == int(uid)).first()
        except Exception:
            pass
    return templates.TemplateResponse("uploaded_exams.html",
                                      {"request": request, "teacher": teacher})


@router.get("/uploads/uploaded-exams-data")
def uploaded_exams_api(request: Request, db: Session = Depends(get_db)):
    uid      = request.session.get("user_id")
    is_admin = request.session.get("is_admin")
    if not uid and not is_admin:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    from app.models.exam    import Exam
    from app.models.student import Student
    from app.models.subject import Subject

    # ── FIX: only return ungraded papers ──────────────────────────
    subs = (db.query(Submission)
            .filter(Submission.status.in_(list(UNGRADED_STATUSES)))
            .order_by(Submission.id.desc()).all())

    files = []
    for sub in subs:
        exam    = db.get(Exam,    sub.exam_id)    if sub.exam_id    else None
        student = db.get(Student, sub.student_id) if sub.student_id else None
        subject = (db.get(Subject, exam.subject_id)
                   if exam and getattr(exam, "subject_id", None) else None)
        mark    = db.query(Mark).filter(Mark.submission_id == sub.id).first()

        fp      = sub.file_path or ""
        size_kb = 0
        if fp:
            p = Path(fp) if Path(fp).exists() else Path(fp.replace("\\", "/"))
            if p.exists():
                try: size_kb = round(p.stat().st_size / 1024, 1)
                except: pass

        name = ""
        if student:
            if hasattr(student, "first_name") and student.first_name:
                name = f"{student.first_name} {student.last_name or ''}".strip()
            else:
                name = getattr(student, "name", "") or ""

        status = sub.status or "uploaded"
        if mark and mark.status and mark.status in UNGRADED_STATUSES:
            status = mark.status

        files.append({
            "submission_id": sub.id,
            "filename":      Path(fp).name if fp else f"submission_{sub.id}.pdf",
            "student_name":  name or f"Student #{sub.student_id}",
            "student_code":  getattr(student, "student_code", "") if student else "",
            "exam_title":    exam.title if exam else f"Exam #{sub.exam_id}",
            "subject_id":    getattr(exam, "subject_id", None) if exam else None,
            "subject_name":  subject.name if subject else "",
            "subject_code":  subject.code if subject else "",
            "semester":      getattr(exam, "semester", None) if exam else None,
            "status":        status,
            "size_kb":       size_kb,
            "grade_url":     f"/uploads/grade-submission/{sub.id}",
            "url":           f"/uploads/open-submission/{sub.id}",
        })
    return JSONResponse({"files": files})


@router.get("/uploads/open-submission/{submission_id}")
def open_submission(submission_id: int, db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if not sub: raise HTTPException(404, "Submission not found")
    fp   = getattr(sub, "file_path", "") or ""
    path = None
    for candidate in [fp, fp.replace("\\", "/")]:
        p = Path(candidate)
        if p.exists(): path = p; break
    if not path:
        path = _find_file(Path(fp).name) if fp else None
    if not path or not path.exists():
        raise HTTPException(404, "File not found")
    return Response(path.read_bytes(), media_type="application/pdf",
                    headers={**NO_CACHE, "Content-Disposition": "inline"})


@router.get("/uploads/download-annotated-pdf/{submission_id}")
def download_annotated_pdf(submission_id: int, db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if not sub: raise HTTPException(404, "Submission not found")
    fp   = getattr(sub, "file_path", "") or ""
    path = None
    for candidate in [fp, fp.replace("\\", "/")]:
        p = Path(candidate)
        if p.exists(): path = p; break
    if not path:
        path = _find_file(Path(fp).name) if fp else None
    if not path or not path.exists():
        raise HTTPException(404, "File not found")
    return Response(path.read_bytes(), media_type="application/pdf",
                    headers={**NO_CACHE,
                             "Content-Disposition": f'attachment; filename="result_{submission_id}.pdf"'})