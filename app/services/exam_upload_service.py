# services/exam_upload_service.py
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.exam import Exam
from app.models.student import Student
from app.models.submission import Submission

UPLOAD_DIR          = Path("uploaded_exams")

def _student_name(s) -> str:
    """Safely get student display name from first_name/last_name or name."""
    try:
        if hasattr(s, "first_name") and s.first_name:
            return f"{s.first_name} {s.last_name or ''}".strip()
        raw = getattr(s, "name", None)
        if raw and not callable(raw):
            return str(raw)
    except Exception:
        pass
    return f"Student #{s.id}"
PDF_DIR             = Path("generated_pdfs")
UPLOADED_PAPERS_DIR = Path("uploaded_papers")
ALLOWED_EXT         = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
PIPELINE            = ["uploaded","assigned","sent_for_marking","marked","reviewed","returned"]

# ── OCR loader ────────────────────────────────────────────────────────────────
def load_ocr():
    try:
        from app.ExamScanner.extractor import extract_fields, scan_image
        print("[OCR] extractor.py loaded OK")
        return extract_fields, scan_image
    except ImportError as e:
        print(f"[OCR] ExamScanner not available: {e}")
    return None, None

_extract_fn, _scan_fn = load_ocr()

def run_ocr(image_path: str, student_map: dict) -> dict:
    empty = {"subject": "", "room": "", "time_slot": "", "annotated_path": ""}
    if _extract_fn:
        try:
            fields         = _extract_fn(image_path)
            if "error" in fields:
                return {"success": False, "error": fields["error"], **empty}
            student_id_raw = (fields.get("student_id") or "").strip()
            name_raw       = (fields.get("name")       or "").strip()
            confidence     = 1.0 if student_id_raw in student_map else (
                             round(0.55 + (0.30 if name_raw else 0), 2) if student_id_raw else 0.0)
            return {
                "success":      bool(student_id_raw),
                "student_code": student_id_raw,
                "student_name": name_raw,
                "confidence":   confidence,
                "subject":      fields.get("subject",""),
                "room":         fields.get("room",""),
                "time_slot":    fields.get("time_slot",""),
                "page_number":  fields.get("page_number",""),
                "annotated_path": "",
                "error": None,
            }
        except Exception as e:
            print(f"[OCR] extractor error: {e}")
    if _scan_fn:
        try:
            result = _scan_fn(image_path, student_map)
            for k in empty: result.setdefault(k, "")
            return result
        except Exception as e:
            return {"success": False, "error": f"OCR error: {e}", **empty}
    return {"success": False, "error": "OCR not available", **empty}

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_date(dt) -> str:
    try:    return dt.strftime("%d %b %Y %H:%M") if dt else "—"
    except: return "—"

def get_page_number(ocr: dict, fallback: int) -> int:
    for key in ("page_number", "detected_page", "ocr_page_number"):
        v = ocr.get(key)
        if isinstance(v, int) and v > 0: return v
        if isinstance(v, str) and v.isdigit() and int(v) > 0: return int(v)
    return fallback

def fail_result(idx, filename, file_path, error) -> dict:
    return {
        "page_number": idx, "ocr_page_number": idx,
        "filename": filename, "file_path": file_path,
        "annotated_path": "", "extracted_id": None, "extracted_name": None,
        "subject": "", "room": "", "time_slot": "",
        "confidence": 0.0, "matched_student": None, "submission_id": None,
        "status": "failed", "needs_review": True, "duplicate": None, "error": error,
    }

def get_students_for_exam(db: Session, exam: Exam) -> list:
    # Always load ALL students for OCR matching — student_code is unique system-wide
    try:
        students = db.query(Student).all()
        return sorted(students, key=lambda s: str(s.id))
    except Exception as e:
        print(f"[UPLOAD] Student query error: {e}")
        return []

def save_exam_page(db, exam_id, page_num, file_path, code, conf, needs_review):
    try:
        from app.models.exam_models import ExamPage
        db.add(ExamPage(
            exam_id=int(exam_id), student_code=code,
            page_number=page_num, file_path=str(file_path),
            extracted_id=code, confidence=conf,
            match_type=("exact" if conf >= 1.0 else ("fuzzy" if conf > 0 else "none")),
            needs_review=needs_review,
        ))
        db.flush()
    except Exception:
        pass

def advance_pipeline(current_status: str) -> str:
    try:
        idx = PIPELINE.index(current_status)
        return PIPELINE[idx + 1] if idx < len(PIPELINE) - 1 else current_status
    except ValueError:
        return PIPELINE[1]

def _sort_pages_cover_first(pages: list) -> list:
    import re as _re
    def _key(r):
        fname = Path(r.get("file_path","") or r.get("filename","")).name
        # Match page-XXXX (dash only) and take the LAST match
        # This avoids matching "page_001" prefix in filenames like
        # "page_001_exam_4_student_29_page-0003.jpg"
        matches = _re.findall(r"page-0*(\d+)", fname, _re.IGNORECASE)
        if matches:
            n = int(matches[-1])  # last match = actual page number
            return 0 if n == 1 else n
        # Fallback to stored page numbers
        n = r.get("ocr_page_number", 0) or r.get("page_number", 0) or 0
        return 0 if n == 1 else (9999 if n == 0 else n)
    return sorted(pages, key=_key)

# ── PDF merge using fitz (PyMuPDF) — most reliable ───────────────────────────
def _merge_to_pdf(exam_id: str, student_id: str, pages: list) -> Path:
    """
    Merge image pages into a single PDF using PyMuPDF (fitz).
    Falls back to Pillow if fitz not available.
    All source images deleted after successful merge.
    """
    up_dir = UPLOADED_PAPERS_DIR / str(exam_id)
    up_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = up_dir / f"{student_id}.pdf"

    pages_sorted = _sort_pages_cover_first(pages)
    image_paths  = [Path(p["file_path"]) for p in pages_sorted]
    image_paths  = [p for p in image_paths if p.exists()]

    print(f"[PDF] Merging {len(image_paths)} pages for student {student_id} → {pdf_path}")
    for i, pg in enumerate(pages_sorted):
        pn = pg.get("ocr_page_number", 0) or pg.get("page_number", 0)
        fp = Path(pg["file_path"])
        print(f"  [{i+1}] page={pn} exists={fp.exists()} file={fp.name}")

    if not image_paths:
        raise ValueError(f"No valid image files found for student {student_id}")

    # Single PDF — copy directly
    if len(image_paths) == 1 and image_paths[0].suffix.lower() == ".pdf":
        shutil.copy2(str(image_paths[0]), str(pdf_path))
        try: image_paths[0].unlink()
        except: pass
        return pdf_path

    # ── Strategy 1: fitz insert_image (most reliable for JPEGs) ──────────────
    try:
        import fitz
        out_doc = fitz.open()

        for img_path in image_paths:
            try:
                if img_path.suffix.lower() == ".pdf":
                    src = fitz.open(str(img_path))
                    out_doc.insert_pdf(src)
                    src.close()
                    print(f"[PDF] fitz: inserted PDF {img_path.name}")
                else:
                    # Use insert_image — most reliable for all JPEG/PNG types
                    # Get image dimensions first
                    try:
                        import struct, imghdr
                        # Try to get dimensions for proper page sizing
                        tmp = fitz.open(str(img_path))
                        tmp_page = tmp[0] if len(tmp) > 0 else None
                        w = tmp_page.rect.width  if tmp_page else 595
                        h = tmp_page.rect.height if tmp_page else 842
                        tmp.close()
                    except Exception:
                        w, h = 595, 842  # A4 default

                    new_page = out_doc.new_page(width=w, height=h)
                    new_page.insert_image(new_page.rect, filename=str(img_path))
                    print(f"[PDF] fitz: inserted image {img_path.name} ({int(w)}x{int(h)})")

            except Exception as e:
                print(f"[PDF] fitz error on {img_path.name}: {e}")
                # Fallback: Pillow
                try:
                    from PIL import Image
                    import io
                    img = Image.open(str(img_path)).convert("RGB")
                    w_px, h_px = img.size
                    # Convert pixels to points (72 dpi)
                    w_pt = w_px * 72 / 150
                    h_pt = h_px * 72 / 150
                    new_page = out_doc.new_page(width=w_pt, height=h_pt)
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    new_page.insert_image(new_page.rect, stream=buf.getvalue())
                    print(f"[PDF] Pillow fallback OK: {img_path.name}")
                except Exception as e2:
                    print(f"[PDF] Both failed for {img_path.name}: {e2}")

        if out_doc.page_count == 0:
            out_doc.close()
            raise ValueError("No pages added to PDF")

        page_count = out_doc.page_count
        out_doc.save(str(pdf_path), deflate=True)
        out_doc.close()
        print(f"[PDF] fitz merged {page_count} pages → {pdf_path} ({pdf_path.stat().st_size} bytes)")

        for p in image_paths:
            try: p.unlink()
            except: pass

        return pdf_path

    except ImportError:
        print("[PDF] fitz not available — falling back to Pillow")

    # ── Strategy 2: Pillow fallback ────────────────────────────────────────────
    try:
        from PIL import Image
        imgs = []
        for p in image_paths:
            if p.suffix.lower() == ".pdf":
                print(f"[PDF] Skipping PDF in Pillow merge: {p.name}")
                continue
            try:
                img = Image.open(str(p)).convert("RGB")
                imgs.append(img)
                print(f"[PDF] Pillow opened: {p.name} {img.size}")
            except Exception as e:
                print(f"[PDF] Pillow cannot open {p.name}: {e}")

        if not imgs:
            raise ValueError("No images could be opened by Pillow")

        imgs[0].save(
            str(pdf_path), format="PDF", save_all=True,
            append_images=imgs[1:], resolution=150,
        )
        print(f"[PDF] Pillow merged {len(imgs)} pages → {pdf_path}")

        for p in image_paths:
            try: p.unlink()
            except: pass

        return pdf_path

    except Exception as e:
        raise ValueError(f"PDF merge failed: {e}")


def _cleanup_exam_dir(exam_dir: Path):
    try:
        files_left = [f for f in exam_dir.rglob("*") if f.is_file()]
        if not files_left:
            shutil.rmtree(str(exam_dir), ignore_errors=True)
            print(f"[UPLOAD] Cleaned up empty temp dir: {exam_dir}")
        else:
            print(f"[UPLOAD] Temp dir kept ({len(files_left)} unmatched files remain): {exam_dir}")
    except Exception as e:
        print(f"[UPLOAD] Cleanup error: {e}")


# ── Main upload logic ─────────────────────────────────────────────────────────
async def process_upload(exam_id: str, files: list, db: Session) -> dict:
    print(f"[UPLOAD] Starting upload for exam_id={exam_id}, {len(files)} file(s)")
    exam = db.query(Exam).filter(Exam.id == int(exam_id)).first()
    if not exam:
        raise HTTPException(404, f"Exam id={exam_id} not found.")

    students    = get_students_for_exam(db, exam)
    student_map = {str(s.student_code): s for s in students if getattr(s, "student_code", None)}
    ocr_map     = {code: {"id": s.id, "name": _student_name(s)} for code, s in student_map.items()}
    print(f"[UPLOAD] Student map keys: {list(student_map.keys())[:5]}...")

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    exam_dir = UPLOAD_DIR / f"exam_{exam_id}_{ts}"
    exam_dir.mkdir(parents=True, exist_ok=True)

    raw_results: List[dict] = []

    for idx, file in enumerate(files, 1):
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            raw_results.append(fail_result(idx, file.filename, "", f"Unsupported type '{ext}'"))
            continue

        safe_name = f"page_{idx:03d}_{Path(file.filename).name}"
        file_path = exam_dir / safe_name
        with open(file_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
        print(f"[UPLOAD] Saved: {file_path.name} ({file_path.stat().st_size} bytes)")

        if ext == ".pdf":
            if len(student_map) == 1:
                only_code    = list(student_map.keys())[0]
                only_student = student_map[only_code]
                raw_results.append({
                    "page_number": idx, "ocr_page_number": idx,
                    "filename": safe_name, "file_path": str(file_path),
                    "annotated_path": "", "extracted_id": only_code,
                    "extracted_name": only__student_name(student),
                    "subject": "", "room": "", "time_slot": "",
                    "confidence": 1.0,
                    "matched_student": {"student_id": only_student.id,
                                        "student_code": only_code,
                                        "student_name": only__student_name(student)},
                    "submission_id": None, "status": "success",
                    "needs_review": False, "duplicate": None, "error": None,
                })
            else:
                raw_results.append({
                    "page_number": idx, "ocr_page_number": idx,
                    "filename": safe_name, "file_path": str(file_path),
                    "annotated_path": "", "extracted_id": None, "extracted_name": None,
                    "subject": "", "room": "", "time_slot": "", "confidence": 0.0,
                    "matched_student": None, "submission_id": None,
                    "status": "unmatched", "needs_review": True,
                    "duplicate": None, "error": "PDF — assign manually",
                })
            continue

        try:
            ocr = run_ocr(str(file_path), ocr_map)
        except Exception as e:
            ocr = {"success": False, "error": str(e), "subject": "", "room": "", "time_slot": "", "annotated_path": ""}

        print(f"[UPLOAD] OCR page {idx}: success={ocr.get('success')} code={ocr.get('student_code')} conf={ocr.get('confidence')}")

        if not ocr.get("success"):
            if len(student_map) == 1:
                only_code    = list(student_map.keys())[0]
                only_student = student_map[only_code]
                raw_results.append({
                    "page_number": idx, "ocr_page_number": idx,
                    "filename": safe_name, "file_path": str(file_path),
                    "annotated_path": "", "extracted_id": only_code,
                    "extracted_name": only__student_name(student),
                    "subject": "", "room": "", "time_slot": "", "confidence": 0.5,
                    "matched_student": {"student_id": only_student.id,
                                        "student_code": only_code,
                                        "student_name": only__student_name(student)},
                    "submission_id": None, "status": "success",
                    "needs_review": True, "duplicate": None, "error": None,
                })
            else:
                raw_results.append(fail_result(idx, safe_name, str(file_path), ocr.get("error")))
                save_exam_page(db, exam_id, idx, file_path, None, 0.0, True)
            continue

        code         = str(ocr.get("student_code") or "").strip()
        confidence   = float(ocr.get("confidence", 0.0) or 0.0)
        student      = student_map.get(code)
        page_num     = get_page_number(ocr, idx)
        needs_review = confidence < 0.8 or student is None
        save_exam_page(db, exam_id, page_num, file_path, code or None, confidence, needs_review)

        raw_results.append({
            "page_number": idx, "ocr_page_number": page_num,
            "filename": safe_name, "file_path": str(file_path),
            "annotated_path": ocr.get("annotated_path", ""),
            "extracted_id": code or None,
            "extracted_name": _student_name(student) if student else ocr.get("student_name"),
            "subject": ocr.get("subject",""), "room": ocr.get("room",""),
            "time_slot": ocr.get("time_slot",""), "confidence": confidence,
            "matched_student": {"student_id": student.id, "student_code": code,
                                "student_name": _student_name(student)} if student else None,
            "submission_id": None,
            "status": "success" if student else "unmatched",
            "needs_review": needs_review, "duplicate": None, "error": None,
        })

    # Group pages by student
    grouped: dict = defaultdict(list)
    final_results: List[dict] = []
    for row in raw_results:
        if row["status"] == "success" and row["extracted_id"] and row["matched_student"]:
            grouped[row["extracted_id"]].append(row)
        else:
            final_results.append(row)

    print(f"[UPLOAD] Grouped students: {list(grouped.keys())}")
    matched = duplicate = 0
    unmatched     = sum(1 for r in final_results if r["status"] in ("unmatched","failed"))
    matched_codes: List[str] = []

    for code, pages in grouped.items():
        student = student_map.get(str(code))
        if not student:
            for row in pages:
                row.update({"status":"unmatched","matched_student":None,"submission_id":None,"needs_review":True})
                final_results.append(row)
            unmatched += len(pages)
            continue

        existing = db.query(Submission).filter(
            Submission.exam_id    == int(exam_id),
            Submission.student_id == student.id,
            Submission.status     != "duplicate",
        ).first()

        # Sort by upload index (page_number) to preserve original order
        pages = sorted(pages, key=lambda r: r.get("page_number", 0))

        if existing:
            print(f"[UPLOAD] Duplicate for student {code} — existing submission {existing.id}")
            duplicate += len(pages)
            dup = {"submission_id": existing.id, "uploaded_at": fmt_date(getattr(existing,"uploaded_at",None))}
            for row in pages:
                row.update({"status":"duplicate","submission_id":existing.id,"duplicate":dup})
                final_results.append(row)
            continue

        print(f"[UPLOAD] Creating submission for student {code} with {len(pages)} page(s)")
        try:
            pdf_path = _merge_to_pdf(exam_id, str(student.id), pages)
            print(f"[UPLOAD] PDF created: {pdf_path} ({pdf_path.stat().st_size} bytes)")

            sub_kw = {
                "exam_id":    int(exam_id),
                "student_id": student.id,
                "file_path":  str(pdf_path),
                "status":     "uploaded",
            }
            if hasattr(Submission, "page_count"):
                sub_kw["page_count"] = len(pages)

            sub = Submission(**sub_kw)
            db.add(sub)
            db.flush()
            print(f"[UPLOAD] Submission id={sub.id}")
            matched += 1
            matched_codes.append(code)

            for row in pages:
                row.update({"status":"success","submission_id":sub.id,"duplicate":None,"file_path":str(pdf_path)})
                final_results.append(row)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[UPLOAD] ERROR for {code}: {e}")
            db.rollback()
            for row in pages:
                row.update({"status":"failed","submission_id":None,"needs_review":True,"error":str(e)})
                final_results.append(row)
            unmatched += len(pages)

    try:
        db.commit()
        print(f"[UPLOAD] Done. matched={matched} duplicate={duplicate} unmatched={unmatched}")
    except Exception as e:
        db.rollback()
        print(f"[UPLOAD] Commit error: {e}")

    _cleanup_exam_dir(exam_dir)
    final_results = sorted(final_results, key=lambda r: r.get("page_number", 0))

    return {
        "success":            True,
        "total_pages":        len(files),
        "processed":          len(final_results),
        "matched_students":   matched,
        "unmatched_students": unmatched,
        "matched_codes":      matched_codes,
        "results":            final_results,
        "message": f"Processed {len(files)} page(s). ✓ Matched: {matched}  ⚠ Unmatched: {unmatched}  ⊘ Duplicates: {duplicate}",
    }


# ── generate_student_pdf ──────────────────────────────────────────────────────
async def generate_student_pdf(
    exam_id: str, student_id: str, student_name: str,
    file_paths: List[str], db: Session,
) -> dict:
    valid = [p for p in file_paths if Path(p).exists()]
    if not valid:
        raise HTTPException(404, "No valid file paths provided")

    gen_dir  = PDF_DIR             / exam_id; gen_dir.mkdir(parents=True, exist_ok=True)
    up_dir   = UPLOADED_PAPERS_DIR / exam_id; up_dir.mkdir(parents=True, exist_ok=True)
    gen_path = gen_dir / f"{student_id}.pdf"
    up_path  = up_dir  / f"{student_id}.pdf"

    pdf_inputs = [p for p in valid if Path(p).suffix.lower() == ".pdf"]
    img_inputs = [p for p in valid if Path(p).suffix.lower() not in (".pdf",)]

    if pdf_inputs and not img_inputs:
        src = Path(pdf_inputs[0])
        if src != up_path: shutil.copy2(str(src), str(up_path))
        shutil.copy2(str(up_path), str(gen_path))
    else:
        # Use fitz for reliable merge
        try:
            import fitz
            out = fitz.open()
            for p in valid:
                path = Path(p)
                try:
                    if path.suffix.lower() == ".pdf":
                        src = fitz.open(str(path)); out.insert_pdf(src); src.close()
                    else:
                        img_doc = fitz.open(str(path))
                        pdfbytes = img_doc.convert_to_pdf(); img_doc.close()
                        src = fitz.open("pdf", pdfbytes); out.insert_pdf(src); src.close()
                except Exception as e:
                    print(f"[PDF] generate skip {path.name}: {e}")
            if out.page_count == 0: raise ValueError("No pages")
            out.save(str(gen_path), deflate=True); out.close()
            shutil.copy2(str(gen_path), str(up_path))
        except ImportError:
            from PIL import Image
            imgs = []
            for p in valid:
                try: imgs.append(Image.open(p).convert("RGB"))
                except: pass
            if not imgs: raise HTTPException(422, "No readable images")
            imgs[0].save(str(gen_path), format="PDF", save_all=True, append_images=imgs[1:], resolution=150)
            shutil.copy2(str(gen_path), str(up_path))

    sub = (db.query(Submission)
           .filter(Submission.exam_id==int(exam_id), Submission.student_id==int(student_id),
                   Submission.status!="duplicate")
           .order_by(Submission.id.desc()).first())
    if sub:
        sub.file_path = str(up_path)
        db.commit(); db.refresh(sub)

    return {
        "success": True, "student_id": student_id, "student_name": student_name,
        "pages_merged": len(valid),
        "pdf_url": f"/api/exams/pdf/{exam_id}/{student_id}.pdf",
        "generated_pdf_path": str(gen_path),
        "uploaded_pdf_path":  str(up_path),
        "submission_id": sub.id if sub else None,
    }