# app/routes/analysis_routes.py
"""
API routes for automatic answer analysis (empty detection + out-of-box writing).
Called by the grading dashboard on load.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.submission import Submission

router = APIRouter(prefix="/api/analysis", tags=["Answer Analysis"])


@router.get("/submission/{submission_id}")
def analyse_submission(submission_id: int, page: int = 0,
                       db: Session = Depends(get_db)):
    """
    Run empty + out-of-box analysis on a submission page.
    Returns per-box results and flags.
    """
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(404, "Submission not found")

    file_path = getattr(sub, "file_path", None)
    if not file_path:
        return {"error": "No file path on submission", "any_empty": False}

    import os
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "any_empty": False}

    try:
        from app.services.answer_analysis_service import analyse_submission_page
        # For now use full-page boxes (whole page = one box)
        # When question box coordinates are available from the exam PDF,
        # pass them here as fractional coordinates
        result = analyse_submission_page(
            pdf_path=file_path,
            page_index=page,
            answer_boxes=[],    # empty = check whole page
            dpi=150,
        )
        return result
    except Exception as e:
        return {"error": str(e), "any_empty": False, "out_of_box": {"has_out_of_box": False}}