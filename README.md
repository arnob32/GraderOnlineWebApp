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

## Testing Instructions for Professors

You can test the application using a single app link and different user roles.

### Docker test steps

1. Open the project folder that contains the Dockerfile and docker-compose.yml.
2. Run:

   ```bash
   docker compose up --build
   ```

3. Open the app in your browser:

   ```text
   http://localhost:8000
   ```

4. Use the following test accounts (if available) or create new ones through the signup/login pages:

   - Admin
   - Teacher
   - Student

5. Test the main features:
   - Login and logout
   - Create or manage exams
   - Upload exam papers
   - Grade submissions
   - View results and export reports

### Stop the app

```bash
docker compose down
```

## Notes

- The app creates required folders automatically when started.
- The default root route redirects to the admin login page.
