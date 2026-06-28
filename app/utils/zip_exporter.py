import io
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List

from app.models.submission import Submission
from app.models.mark import Mark


ALLOWED = {".pdf", ".png", ".jpg", ".jpeg"}
UPLOAD_DIRS = ["uploaded_papers", "uploaded_exams", "uploads", "Uploads"]


def _find_file(file_path: str) -> Path | None:
    """Find a submission file on disk."""
    if not file_path:
        return None
    # Try the stored path directly first
    p = Path(file_path.replace("\\", "/"))
    if p.exists() and p.is_file():
        return p
    # Search upload dirs by filename
    name = Path(file_path).name
    for d in UPLOAD_DIRS:
        for root, _, files in os.walk(d):
            if name in files:
                found = Path(root) / name
                if found.is_file():
                    return found
    return None


def _safe_filename(student_name: str, student_code: str, submission_id: int,
                   original: Path) -> str:
    """Build a clean filename for the zip entry."""
    name = (student_code or student_name or f"student_{submission_id}")
    # Strip characters unsafe in filenames
    name = "".join(c for c in name if c.isalnum() or c in "-_")
    return f"{name}{original.suffix.lower()}"


def zip_exam_annotated_pdfs(
    exam_id: int,
    exam_title: str,
    submissions: List[Submission],
    marks: dict,       # {submission_id: Mark}
    students: dict,    # {student_id: Student}
) -> bytes:
    """
    Build an in-memory ZIP of all annotated submission files for an exam.
    Returns raw bytes of the ZIP file.
    """
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        added = 0
        for sub in submissions:
            file_path = _find_file(str(sub.file_path) if sub.file_path else "")
            if not file_path:
                continue

            student  = students.get(sub.student_id)
            s_name   = getattr(student, "name",         "") if student else ""
            s_code   = getattr(student, "student_code", "") if student else ""
            mark     = marks.get(sub.id)
            score    = getattr(mark, "score",        None)
            max_sc   = getattr(mark, "max_score",    None)
            grade    = getattr(mark, "letter_grade", "")  or ""

            # Build filename: CODE_NAME_score.pdf
            score_str = f"{int(score)}" if score is not None else "ungraded"
            base      = (s_code or s_name or f"sub{sub.id}")
            base      = "".join(c for c in base if c.isalnum() or c in "-_")
            arcname   = f"{base}_{score_str}{file_path.suffix.lower()}"

            zf.write(str(file_path), arcname=arcname)
            added += 1

        # Add a summary CSV inside the zip
        lines = ["student_code,student_name,submission_id,score,max_score,grade,status"]
        for sub in submissions:
            student = students.get(sub.student_id)
            mark    = marks.get(sub.id)
            code    = getattr(student, "student_code", "") if student else ""
            name    = getattr(student, "name",         "") if student else f"#{sub.student_id}"
            score   = getattr(mark, "score",        "") if mark else ""
            max_sc  = getattr(mark, "max_score",    "") if mark else ""
            grade   = getattr(mark, "letter_grade", "") if mark else ""
            lines.append(f"{code},{name},{sub.id},{score},{max_sc},{grade},{sub.status}")

        zf.writestr("_summary.csv", "\n".join(lines))

    buf.seek(0)
    return buf.read()