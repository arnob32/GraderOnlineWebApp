from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import secrets
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from app.database import engine
from app.models.base import Base
import app.models

from app.routes.auth_routes              import router as auth_routes
from app.routes.admin_routes             import router as admin_routes
from app.routes.marking_routes           import router as marking_routes
from app.routes.department_routes        import router as department_routes
from app.routes.semester_routes          import router as semester_routes
from app.routes.unmatched_routes         import router as unmatched_routes
from app.routes.teacher_dashboard_routes import router as teacher_dashboard_routes
from app.routes.student_dashboard_routes import router as student_dashboard_routes
from app.routes.exam_routes              import router as exam_routes
from app.routes.exam_upload              import router as exam_upload_router, page_router
from app.routes.feedback_template_routes import router as feedback_template_routes
from app.routes.student_auth_routes      import router as student_auth_routes
from app.routes.analysis_routes          import router as analysis_routes
from app.routes.uploaded_exams_routes    import router as uploaded_exams_routes
from app.routes.student_results_routes   import router as student_results_routes
from app.routes.results_exports_routes   import router as results_exports_routes

# Ensure directories exist before mounting as static
os.makedirs("uploaded_exams",  exist_ok=True)
os.makedirs("generated_pdfs",  exist_ok=True)
os.makedirs("uploaded_papers", exist_ok=True)

app = FastAPI(title="ExamMark")
app.add_middleware(SessionMiddleware, secret_key="change-this-secret-key-in-production", max_age=0, https_only=False, same_site="lax")
Base.metadata.create_all(bind=engine)

app.include_router(uploaded_exams_routes)
app.include_router(auth_routes, prefix="/auth")
app.include_router(admin_routes)
app.include_router(teacher_dashboard_routes)
app.include_router(student_dashboard_routes)
app.include_router(student_auth_routes)
app.include_router(department_routes)
app.include_router(semester_routes)
app.include_router(exam_routes)
app.include_router(marking_routes)
app.include_router(exam_upload_router)
app.include_router(page_router)
app.include_router(unmatched_routes)
app.include_router(feedback_template_routes)
app.include_router(analysis_routes)
app.include_router(student_results_routes)
app.include_router(results_exports_routes)

app.mount("/static",         StaticFiles(directory="app/static"),     name="static")
app.mount("/generated_pdfs", StaticFiles(directory="generated_pdfs"), name="generated_pdfs")
app.mount("/uploaded_exams", StaticFiles(directory="uploaded_exams"), name="uploaded_exams")

@app.get("/")
def root():
    return RedirectResponse(url="/admin/login")