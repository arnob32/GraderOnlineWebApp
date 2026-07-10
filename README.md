# GraderOnline

ExamMark is a FastAPI-based web application for managing exams, uploading scanned papers, grading submissions, and exporting results. It includes separate interfaces for administrators, teachers, and students.

## Features

- Admin, teacher, and student authentication
- Exam creation and management
- OCR-based exam upload and processing
- Marking and feedback workflows
- Result export and PDF generation
- Uploaded exam and unmatched page tracking

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- Jinja2 templates
- SQLite (default database)
- Docker Compose support

## Prerequisites

- Python 3.9+
- pip
- Optional: Docker and Docker Compose

## Setup

1. Clone the repository
2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Run the Application

### Local development

```bash
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000 in your browser.

### With Docker

```bash
docker compose up --build
```

The app will be available at http://localhost:8000.

## Project Structure

- app/ - FastAPI app, routes, models, services, templates, and static files
- uploaded_exams/ - uploaded exam files
- uploaded_papers/ - processed paper uploads
- generated_pdfs/ - generated PDF outputs
- outputs/ - output artifacts

## Notes

- The app creates required folders automatically when started.
- The default root route redirects to the admin login page.
