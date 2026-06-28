# routes/unmatched_routes.py
import os
import shutil

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student

router    = APIRouter(prefix="/unmatched", tags=["Unmatched Pages"])
templates = Jinja2Templates(directory="app/templates")

UNMATCHED_DIR = "unmatched_pages"
os.makedirs(UNMATCHED_DIR, exist_ok=True)


@router.get("", response_class=HTMLResponse)
def unmatched_list(request: Request, db: Session = Depends(get_db)):
    files    = sorted([f for f in os.listdir(UNMATCHED_DIR)
                       if f.lower().endswith((".png", ".jpg", ".jpeg"))])
    students = db.query(Student).all()
    return templates.TemplateResponse("unmatched_pages.html",
                                      {"request": request, "files": files,
                                       "students": students})


@router.post("/assign")
def assign_unmatched(filename: str = Form(...), student_code: str = Form(...)):
    src = os.path.join(UNMATCHED_DIR, filename)
    if not os.path.exists(src):
        return RedirectResponse("/unmatched", status_code=303)
    dst_dir = os.path.join("uploaded_exams", "manual_assigned", student_code)
    os.makedirs(dst_dir, exist_ok=True)
    shutil.move(src, os.path.join(dst_dir, filename))
    return RedirectResponse("/unmatched", status_code=303)