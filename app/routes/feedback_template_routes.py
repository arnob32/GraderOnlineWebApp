# app/routes/feedback_template_routes.py
"""
CRUD routes for grading feedback templates.
Templates are scoped per question + optionally per exam + per teacher.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.feedback_template import FeedbackTemplate

router = APIRouter(prefix="/api/feedback-templates", tags=["Feedback Templates"])


class TemplateIn(BaseModel):
    label:       str
    points:      float
    style:       str = "add"          # "add" | "subtract"
    description: Optional[str] = None
    question_id: Optional[int] = None
    exam_id:     Optional[int] = None
    teacher_id:  Optional[int] = None
    sort_order:  int = 0


@router.get("")
def list_templates(
    question_id: Optional[int] = None,
    exam_id:     Optional[int] = None,
    teacher_id:  Optional[int] = None,
    style:       Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Return templates matching the given scope.
    Precedence: question-level > exam-level > teacher-level (global).
    All matching templates are returned; the frontend groups them.
    """
    q = db.query(FeedbackTemplate)
    filters = []
    if question_id is not None:
        filters.append(FeedbackTemplate.question_id == question_id)
    if exam_id is not None:
        filters.append(FeedbackTemplate.exam_id == exam_id)
    if teacher_id is not None:
        filters.append(FeedbackTemplate.teacher_id == teacher_id)
    if filters:
        from sqlalchemy import or_
        q = q.filter(or_(*filters))
    if style:
        q = q.filter(FeedbackTemplate.style == style)
    q = q.order_by(FeedbackTemplate.sort_order, FeedbackTemplate.id)
    return [t.to_dict() for t in q.all()]


@router.post("")
def create_template(payload: TemplateIn, db: Session = Depends(get_db)):
    if not payload.label.strip():
        raise HTTPException(400, "label is required")
    t = FeedbackTemplate(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t.to_dict()


@router.put("/{template_id}")
def update_template(template_id: int, payload: TemplateIn,
                    db: Session = Depends(get_db)):
    t = db.query(FeedbackTemplate).filter(
        FeedbackTemplate.id == template_id).first()
    if not t:
        raise HTTPException(404, "Template not found")
    for k, v in payload.model_dump().items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t.to_dict()


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    t = db.query(FeedbackTemplate).filter(
        FeedbackTemplate.id == template_id).first()
    if not t:
        raise HTTPException(404, "Template not found")
    db.delete(t)
    db.commit()
    return {"ok": True}


@router.post("/bulk")
def create_bulk(templates: list[TemplateIn], db: Session = Depends(get_db)):
    """Create multiple templates at once (e.g. copy from another question)."""
    created = []
    for payload in templates:
        t = FeedbackTemplate(**payload.model_dump())
        db.add(t)
        created.append(t)
    db.commit()
    for t in created:
        db.refresh(t)
    return [t.to_dict() for t in created]