from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os
import textwrap
from PIL import Image

OUTPUT_DIR     = "generated_pdfs"
TEMP_IMAGE_DIR = "temp_question_images"
os.makedirs(OUTPUT_DIR,     exist_ok=True)
os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)


def generate_exam_pdf(
    exam, student, questions: list,
    question_image_paths: dict | None = None,
    reference_boxes:      list | None = None,
    db=None,              # SQLAlchemy session — pass to save box coords
    db_questions=None,    # list of Question ORM objects in same order as questions
):
    if question_image_paths is None: question_image_paths = {}
    if reference_boxes      is None: reference_boxes      = []

    filename  = f"exam_{exam.id}_student_{student.id}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)
    c         = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    PAGE_NUM = 1
    LEFT         = 15
    TOP_MARGIN   = 87
    HEADER_Y     = 10
    BOX_LEFT     = 20
    BOX_RIGHT    = width - 15

    COVER_TOP_LINE   = 210
    COVER_LAST_NAME  = 120
    COVER_STUDENT_ID = 50
    COVER_DIVIDER    = 50
    COVER_INSTRUCT   = 50
    COVER_BOX        = 50
    COVER_RIGHT      = 71

    WRAP_WIDTH      = 100
    WRAP_WIDTH_CONT = 105
    MCQ_WRAP_WIDTH  = 105
    Q_LINE_GAP    = 15
    Q_LABEL_DROP  = 3.5
    PRE_BOX_GAP   = -5
    POST_BOX_GAP  = 8
    POST_MCQ_GAP  = 6
    MCQ_OPT_LEAD  = 10
    MCQ_OPT_EXTRA = 5
    IMG_BELOW_GAP = 6
    Q_GAP         = 4

    BOX_HEIGHTS = {
        "small":    85,
        "medium":  225,
        "large":   242,
        "fullPage":692,
        "mcq":      80,
        "diagram":  198,
    }
    BOX_LINES = {
        "small":    7,
        "medium":   16,
        "large":    20,
        "fullPage": 29,
    }
    COLORS = {
        "text":               (0.10, 0.12, 0.16),
        "muted":              (0.38, 0.42, 0.49),
        "rule":               (0.16, 0.18, 0.22),
        "line":               (0.74, 0.78, 0.84),
        "box":                (0.18, 0.20, 0.24),
        "box_line":           (0.78, 0.81, 0.86),
        "option_fill":        (0.985, 0.989, 0.997),
        "option_stroke":      (0.82,  0.86,  0.92),
        "option_badge_fill":  (0.955, 0.965, 0.995),
        "option_badge_stroke":(0.66,  0.72,  0.86),
        "option_badge_text":  (0.24,  0.32,  0.58),
    }

    # ── Save box coordinates back to DB ──────────────────────────────────────
    def save_box(q_index, bx, by, bw, bh, page):
        """Save answer-box coordinates to the Question row in the DB."""
        if db is None or db_questions is None:
            return
        try:
            # q_index is 1-based (matches enumerate start=1)
            if q_index < 1 or q_index > len(db_questions):
                return
            qrow = db_questions[q_index - 1]
            if qrow is None:
                return
            qrow.box_x    = float(bx)
            qrow.box_y    = float(by)   # bottom of box in PDF coords (y from bottom)
            qrow.box_w    = float(bw)
            qrow.box_h    = float(bh)
            qrow.box_page = int(page)
            db.flush()
        except Exception as e:
            print(f"[PDF] Could not save box coords for Q{q_index}: {e}")

    def draw_corners():
        c.setLineWidth(1.5)
        c.setStrokeColorRGB(0.15, 0.15, 0.15)
        c.line(LEFT, height - TOP_MARGIN, LEFT, 10)
        c.line(LEFT, height - TOP_MARGIN, width - 10, height - TOP_MARGIN)
        c.line(width - 10, height - TOP_MARGIN, width - 10, 10)
        c.line(LEFT, 10, width - 10, 10)
        c.setStrokeColorRGB(0, 0, 0)

    def draw_header():
        nonlocal PAGE_NUM
        draw_corners()
        last_name  = getattr(student, "last_name",  None) or student.name.split()[-1]
        first_name = getattr(student, "first_name", None) or student.name.split()[0]
        c.setFont("Times-Roman", 16)
        c.setFillColorRGB(*COLORS["text"])
        c.drawString(LEFT + 120, height - HEADER_Y - 45,
                     f"{student.student_code}, {last_name}, {first_name}")
        c.drawRightString(width - 120, height - HEADER_Y - 45,
                          f"Page {PAGE_NUM} of {TOTAL_PAGES}")
        c.setFillColorRGB(*COLORS["text"])

    def new_page():
        nonlocal PAGE_NUM
        PAGE_NUM += 1
        c.showPage()
        draw_header()
        return height - TOP_MARGIN - 15

    def get_exam_value(*names, default=None):
        for name in names:
            if isinstance(exam, dict) and name in exam and exam.get(name) is not None:
                return exam.get(name)
            value = getattr(exam, name, None)
            if value is not None:
                return value
        return default

    def normalize_answer_type(a):
        if not a: return "small"
        a = str(a).strip().lower()
        if a in ("mmcq","m_mcq","multi_mcq","multiplechoice","multiple_choice","choice","mcqs"):
            return "mcq"
        if a in ("fullpge","full_page","fullpage"):
            return "fullPage"
        if a in ("veryshort","very_short","short","brief","oneshort"):
            return "small"
        if a in ("essay","long","descriptive","theory"):
            return "large"
        if a in ("diagram","drawing","draw","diagramspace","diagram_space","drawing_space"):
            return "diagram"
        return a

    def get_mcq_options(q):
        opts = q.get("options") or q.get("choices") or q.get("mcq_options") or []
        if isinstance(opts, str):
            opts = [x.strip() for x in (opts.split("\n") if "\n" in opts else opts.split(",")) if x.strip()]
        if not isinstance(opts, (list, tuple)): opts = [str(opts)]
        return [str(o) for o in opts if str(o).strip()]

    def normalize_question_number(value, fallback_index):
        if value is None: return str(fallback_index)
        number = str(value).strip()
        if not number: return str(fallback_index)
        if number.lower().startswith("q"): number = number[1:].strip()
        return number or str(fallback_index)

    def is_group_parent_question(q):
        if not isinstance(q, dict): return False
        if q.get("is_group_parent") is True or q.get("has_subquestions") is True: return True
        return str(q.get("answer_type","")).strip().lower() in {"group","parent","heading"}

    def get_image_display_size(image_path, max_width=420, max_height=200):
        try:
            with Image.open(image_path) as img:
                w, h = img.size
            if w <= 0 or h <= 0: return None
            scale = min(max_width / w, max_height / h, 1.0)
            return w * scale, h * scale
        except Exception:
            return None

    def ensure_space(current_y, needed_height):
        if current_y - needed_height < 5:
            return new_page()
        return current_y

    def draw_wrapped_text(lines, x, current_y, font_name="Helvetica", font_size=12, line_gap=None):
        if line_gap is None: line_gap = Q_LINE_GAP
        c.setFont(font_name, font_size)
        for line in lines:
            c.drawString(x, current_y, line)
            current_y -= line_gap
        return current_y

    def draw_answer_box(x, y, box_width, box_height, answer_type):
        c.setLineWidth(1.05)
        c.setStrokeColorRGB(*COLORS["box"])
        c.roundRect(x, y - box_height, box_width, box_height, 6, stroke=1, fill=0)
        if answer_type == "diagram":
            c.setFont("Helvetica-Oblique", 9.5)
            c.setFillColorRGB(*COLORS["muted"])
            c.drawString(x + 10, y - 16, "For diagram Only")
            c.setFillColorRGB(*COLORS["text"])
            c.setLineWidth(0.4)
            c.setStrokeColorRGB(*COLORS["line"])
            c.line(x + 12, y - box_height + 20, x + box_width - 12, y - box_height + 20)
            c.setStrokeColorRGB(*COLORS["box"])
            return
        n_lines = BOX_LINES.get(answer_type, 0)
        if n_lines > 0:
            c.setLineWidth(0.30)
            c.setStrokeColorRGB(*COLORS["box_line"])
            spacing = (box_height - 10) / (n_lines + 1)
            for ln in range(1, n_lines + 1):
                ly = y - 5 - ln * spacing
                c.line(x + 10, ly, x + box_width - 10, ly)
        c.setStrokeColorRGB(*COLORS["box"])

    def draw_reference_box(box_size, linked_question, current_y):
        box_h = BOX_HEIGHTS.get(box_size, BOX_HEIGHTS["medium"])
        label_height = 7
        needed = label_height + PRE_BOX_GAP + box_h + POST_BOX_GAP
        current_y = ensure_space(current_y, needed)
        c.setFont("Helvetica-Oblique", 9.5)
        c.setFillColorRGB(*COLORS["muted"])
        c.drawString(LEFT + 5, current_y,
                     "[Reference box for extra writing]" if linked_question else "[Reference]")
        c.setFillColorRGB(*COLORS["text"])
        current_y -= label_height
        draw_answer_box(BOX_LEFT, current_y, BOX_RIGHT - BOX_LEFT, box_h, box_size)
        current_y -= box_h + POST_BOX_GAP
        return current_y

    def draw_marks(marks, y):
        if marks is not None and str(marks).strip():
            try:    marks_val = int(float(str(marks).strip()))
            except: marks_val = str(marks).strip()
            c.setFont("Helvetica", 9.5)
            c.setFillColorRGB(*COLORS["muted"])
            c.drawRightString(width - LEFT, y, f"[{marks_val}]")
            c.setFillColorRGB(*COLORS["text"])

    def draw_mcq_option(label, text_value, current_y):
        wrapped = textwrap.wrap(text_value, MCQ_WRAP_WIDTH) or [""]
        PADDING = 5; LINE_H = 10
        option_height = max(32, PADDING * 2 + len(wrapped) * LINE_H)
        current_y = ensure_space(current_y, option_height + 6)
        box_x = LEFT + 20; box_w = BOX_RIGHT - box_x - 4
        box_y = current_y - option_height
        c.setFillColorRGB(*COLORS["option_fill"])
        c.setStrokeColorRGB(*COLORS["option_stroke"])
        c.setLineWidth(0.8)
        c.roundRect(box_x, box_y, box_w, option_height, 7, stroke=1, fill=1)
        badge_size = 22; badge_x = box_x + 10
        badge_cy = box_y + option_height / 2; badge_y = badge_cy - badge_size / 2
        c.setFillColorRGB(*COLORS["option_badge_fill"])
        c.setStrokeColorRGB(*COLORS["option_badge_stroke"])
        c.roundRect(badge_x, badge_y, badge_size, badge_size, 6, stroke=1, fill=1)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(*COLORS["option_badge_text"])
        c.drawCentredString(badge_x + badge_size / 2, badge_y + badge_size * 0.28, label)
        text_x = badge_x + badge_size + 12
        text_y = box_y + option_height - PADDING - LINE_H - 3
        c.setFillColorRGB(*COLORS["text"])
        c.setFont("Helvetica", 10.8)
        for line in wrapped:
            c.drawString(text_x, text_y, line)
            text_y -= LINE_H
        return box_y - 6

    def draw_cover_page():
        nonlocal PAGE_NUM
        last_name   = getattr(student, "last_name",  None) or student.name.split()[-1]
        first_name  = getattr(student, "first_name", None) or student.name.split()[0]
        course_code = getattr(exam, "course_code", "") or ""
        exam_date   = getattr(exam, "exam_date",   "") or ""
        exam_time   = getattr(exam, "exam_time",   "") or ""
        cover_rules = get_exam_value("cover_rules","instructions","rules",default="") or ""
        subject_code = ""
        try:
            subj = getattr(exam, "subject", None)
            if subj: subject_code = getattr(subj, "code", "") or ""
            if not subject_code: subject_code = getattr(exam, "subject_code", "") or ""
            if not subject_code: subject_code = course_code
        except: subject_code = course_code

        info_parts = [exam.title]
        if subject_code: info_parts.append(subject_code)
        if exam_date:    info_parts.append(exam_date)
        if exam_time:    info_parts.append(exam_time)
        title_text = ", ".join(info_parts)

        c.setFont("Helvetica", 12)
        c.setFillColorRGB(*COLORS["text"])
        c.drawString(COVER_TOP_LINE, height - 42, title_text)
        c.setFont("Times-Bold", 50)
        c.drawString(COVER_LAST_NAME, height - 118, last_name.upper())
        c.setFont("Times-Roman", 16)
        c.drawString(COVER_STUDENT_ID, height - 140, f"Student-ID: {student.student_code}")
        c.drawString(COVER_STUDENT_ID, height - 162, f"Name: {last_name}, {first_name}")
        c.setLineWidth(0.8)
        c.setStrokeColorRGB(*COLORS["rule"])
        c.line(COVER_DIVIDER, height - 172, width - COVER_RIGHT, height - 172)
        c.setFont("Times-Bold", 16)
        c.setFillColorRGB(*COLORS["text"])
        c.drawString(COVER_INSTRUCT, height - 192, "Follow The Below Instructions: .")
        y0 = height - 214
        if cover_rules.strip():
            for para in [p.strip() for p in cover_rules.splitlines() if p.strip()]:
                for line in textwrap.wrap(para, 72) or [""]:
                    c.drawString(COVER_INSTRUCT, y0, line); y0 -= 22
                y0 -= 4
        else:
            for line in ["1 point = 1 minute for reading and writing.",
                         "A scientific calculator is allowed to use."]:
                c.drawString(COVER_INSTRUCT, y0, line); y0 -= 22
        footer_bg_height = 96
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.rect(0, 0, width, footer_bg_height, stroke=0, fill=1)
        c.rect(0, 0, width, 26,               stroke=0, fill=1)
        box_top = y0 - 8; box_bot = footer_bg_height + 70; box_h = box_top - box_bot
        if box_h > 40:
            c.setFillColorRGB(0.97, 0.97, 0.99)
            c.setStrokeColorRGB(*COLORS["box"])
            c.setLineWidth(1.2)
            c.roundRect(COVER_BOX, box_bot, width - COVER_BOX - 40, box_h, 8, stroke=1, fill=1)
            c.setFont("Helvetica-Bold", 9)
            c.setFillColorRGB(*COLORS["muted"])
            c.drawString(COVER_BOX + 10, box_top - 14, "Examiner Part Only:")
            c.setLineWidth(0.45)
            c.setStrokeColorRGB(*COLORS["line"])
            c.line(COVER_BOX + 10, box_top - 20, width - COVER_RIGHT - 10, box_top - 20)
        c.setFillColorRGB(*COLORS["text"])
        PAGE_NUM += 1
        c.showPage()

    def count_exam_pages():
        sim_y = height - TOP_MARGIN - 15
        sim_pages = 1
        for qi, q in enumerate(questions, start=1):
            qat    = normalize_answer_type(q.get("answer_type", "small"))
            is_grp = is_group_parent_question(q)
            if is_grp:
                qat = normalize_answer_type(q.get("answer_type", "large"))
                if qat in ("group","parent","heading",""): qat = "large"
            qt  = q.get("text", "") or ""
            ql  = f"Q{qi}:"
            is_s = str(q.get("level","main")).strip().lower() == "sub"
            flw  = max(42, (WRAP_WIDTH + 10 if is_s else WRAP_WIDTH) - max(8, int(len(ql) * 0.65)))
            wf   = textwrap.wrap(qt, flw) if qt else [""]
            wc   = textwrap.wrap(qt[len(wf[0]):].strip(), WRAP_WIDTH_CONT) if len(wf) > 1 else []
            total_lines = 1 + len(wc)
            box_h = BOX_HEIGHTS.get(qat, 48)
            if qat == "fullPage":
                full_box_h = BOX_HEIGHTS["fullPage"]
                q_block = Q_LABEL_DROP + total_lines * Q_LINE_GAP + PRE_BOX_GAP + full_box_h + POST_BOX_GAP + Q_GAP
                if sim_y - q_block < 5: sim_pages += 1; sim_y = height - TOP_MARGIN - 15
                if qi > 1: sim_y -= Q_GAP
                sim_y -= Q_LABEL_DROP + total_lines * Q_LINE_GAP + PRE_BOX_GAP + 6 + full_box_h + POST_BOX_GAP
                continue
            if is_grp:
                needed = Q_LABEL_DROP + total_lines * Q_LINE_GAP + Q_GAP
                if sim_y - needed < 5: sim_pages += 1; sim_y = height - TOP_MARGIN - 15
                if qi > 1: sim_y -= Q_GAP
                sim_y -= Q_LABEL_DROP + 6.5 + (total_lines - 1) * Q_LINE_GAP
                continue
            if qat == "mcq":
                opts = get_mcq_options(q)
                opt_lines = sum(len(textwrap.wrap(o, 80) or [""]) for o in opts)
                needed = (Q_LABEL_DROP + total_lines * Q_LINE_GAP
                          + opt_lines * MCQ_OPT_LEAD + len(opts) * MCQ_OPT_EXTRA + POST_MCQ_GAP)
            else:
                needed = Q_LABEL_DROP + total_lines * Q_LINE_GAP + PRE_BOX_GAP + box_h + POST_BOX_GAP
            if sim_y - needed < 5: sim_pages += 1; sim_y = height - TOP_MARGIN - 15
            if qi > 1: sim_y -= Q_GAP
            sim_y -= Q_LABEL_DROP + 6.5 + (total_lines - 1) * Q_LINE_GAP + PRE_BOX_GAP
            if qat == "mcq": sim_y -= opt_lines * MCQ_OPT_LEAD + len(opts) * MCQ_OPT_EXTRA + POST_MCQ_GAP
            else:             sim_y -= box_h + POST_BOX_GAP
        for rb in reference_boxes:
            rb_size = normalize_answer_type(rb.get("size","medium"))
            if rb_size not in BOX_HEIGHTS: rb_size = "medium"
            rb_box_h = BOX_HEIGHTS[rb_size]
            needed_rb = 22 + PRE_BOX_GAP + rb_box_h + POST_BOX_GAP
            if sim_y - needed_rb < 5: sim_pages += 1; sim_y = height - TOP_MARGIN - 15
            sim_y -= Q_GAP + needed_rb
        return sim_pages

    TOTAL_PAGES = 1 + count_exam_pages()
    draw_cover_page()
    draw_header()
    y = height - TOP_MARGIN - 15

    for i, q in enumerate(questions, start=1):
        question_text = q.get("text", "") or ""
        marks         = q.get("marks", "")
        q_number      = normalize_question_number(q.get("number"), i)
        q_label       = f"Q{q_number}:"
        is_sub        = str(q.get("level","main")).strip().lower() == "sub"
        q_left        = LEFT
        q_box_left    = BOX_LEFT
        q_box_right   = BOX_RIGHT

        first_line_wrap = max(42, (WRAP_WIDTH + 10 if is_sub else WRAP_WIDTH) - max(8, int(len(q_label) * 0.65)))
        wrapped_first   = textwrap.wrap(question_text, first_line_wrap) if question_text else [""]
        remaining_text  = question_text[len(wrapped_first[0]):].strip() if len(wrapped_first) > 1 else ""
        wrapped_cont    = textwrap.wrap(remaining_text, WRAP_WIDTH_CONT) if remaining_text else []
        total_q_lines   = 1 + len(wrapped_cont)
        is_group_parent = is_group_parent_question(q)
        answer_type     = normalize_answer_type(q.get("answer_type","small")) if not is_group_parent else "group"

        image_path         = question_image_paths.get(i)
        image_size         = None
        image_height_needed = 0
        if image_path and os.path.exists(image_path):
            image_size = get_image_display_size(image_path)
            if image_size: _, img_h = image_size; image_height_needed = img_h + IMG_BELOW_GAP

        if is_group_parent:
            parent_type = normalize_answer_type(q.get("answer_type","large"))
            if parent_type in ("group","parent","heading",""): parent_type = "large"
            box_h = BOX_HEIGHTS.get(parent_type, BOX_HEIGHTS["large"])
            needed_height = Q_LABEL_DROP + total_q_lines * Q_LINE_GAP + image_height_needed + PRE_BOX_GAP + box_h + POST_BOX_GAP + Q_GAP
            y = ensure_space(y, needed_height)
            if i > 1: y -= Q_GAP
            c.setFont("Helvetica-Bold", 12); c.setFillColorRGB(*COLORS["text"])
            c.drawString(LEFT + 5, y, q_label)
            label_w = c.stringWidth(q_label, "Helvetica-Bold", 12)
            c.setFont("Helvetica", 12)
            c.drawString(LEFT + label_w + 5, y + 1, wrapped_first[0])
            y -= Q_LABEL_DROP + 6.5
            if wrapped_cont: y = draw_wrapped_text(wrapped_cont, LEFT + 5, y, font_name="Helvetica", font_size=12, line_gap=14)
            y -= PRE_BOX_GAP
            if image_size and image_path and os.path.exists(image_path):
                img_w, img_h = image_size; y = ensure_space(y, img_h + IMG_BELOW_GAP)
                img_x = (width - img_w) / 2
                c.drawImage(ImageReader(image_path), img_x, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask="auto")
                y -= img_h + IMG_BELOW_GAP
            continue

        if answer_type == "fullPage":
            full_box_h = BOX_HEIGHTS["fullPage"]
            q_block = Q_LABEL_DROP + total_q_lines * Q_LINE_GAP + image_height_needed + PRE_BOX_GAP + full_box_h + POST_BOX_GAP + Q_GAP
            y = ensure_space(y, q_block)
            if i > 1: y -= Q_GAP
            qfs = 11.4 if is_sub else 12
            c.setFont("Helvetica-Bold", qfs); c.setFillColorRGB(*COLORS["text"])
            c.drawString(q_left + 5, y, q_label)
            label_w = c.stringWidth(q_label, "Helvetica-Bold", qfs)
            c.setFont("Helvetica", qfs - 0.3)
            c.drawString(q_left + label_w + 8, y, wrapped_first[0])
            draw_marks(marks, y)
            y -= Q_LABEL_DROP
            if wrapped_cont: y = draw_wrapped_text(wrapped_cont, q_left, y, font_name="Helvetica", font_size=12, line_gap=18)
            y -= PRE_BOX_GAP
            if image_size and image_path and os.path.exists(image_path):
                img_w, img_h = image_size; y = ensure_space(y, img_h + IMG_BELOW_GAP)
                img_x = (width - img_w) / 2
                c.drawImage(ImageReader(image_path), img_x, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask="auto")
                y -= img_h + IMG_BELOW_GAP
            y -= 6
            y = ensure_space(y, full_box_h + POST_BOX_GAP)
            draw_answer_box(q_box_left, y, q_box_right - q_box_left, full_box_h, "fullPage")
            # ── Save box coords ──
            save_box(i, q_box_left, y - full_box_h, q_box_right - q_box_left, full_box_h, PAGE_NUM)
            y -= full_box_h + POST_BOX_GAP
            continue

        if answer_type == "mcq":
            options      = get_mcq_options(q)
            wrapped_opts = [textwrap.wrap(opt, 80) or [""] for opt in options]
            opt_lines    = sum(len(w) for w in wrapped_opts)
            needed_height = (Q_LABEL_DROP + total_q_lines * Q_LINE_GAP + image_height_needed
                             + opt_lines * MCQ_OPT_LEAD + len(options) * MCQ_OPT_EXTRA + POST_MCQ_GAP + Q_GAP)
        else:
            box_h         = BOX_HEIGHTS.get(answer_type, 48)
            needed_height = (Q_LABEL_DROP + total_q_lines * Q_LINE_GAP + image_height_needed
                             + PRE_BOX_GAP + box_h + POST_BOX_GAP)

        y = ensure_space(y, needed_height)
        if i > 1: y -= Q_GAP
        qfs = 11.4 if is_sub else 12
        c.setFont("Helvetica-Bold", qfs); c.setFillColorRGB(*COLORS["text"])
        c.drawString(q_left + 5, y, q_label)
        label_w = c.stringWidth(q_label, "Helvetica-Bold", qfs)
        c.setFont("Helvetica", qfs - 0.3)
        c.drawString(q_left + label_w + 8, y, wrapped_first[0])
        draw_marks(marks, y)
        y -= Q_LABEL_DROP + 6.5
        if wrapped_cont: y = draw_wrapped_text(wrapped_cont, q_left + 5, y, font_name="Helvetica", font_size=10.8)
        y -= PRE_BOX_GAP

        if image_size and image_path and os.path.exists(image_path):
            img_w, img_h = image_size; y = ensure_space(y, img_h + IMG_BELOW_GAP)
            img_x = (width - img_w) / 2
            c.drawImage(ImageReader(image_path), img_x, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask="auto")
            y -= img_h + IMG_BELOW_GAP

        if answer_type == "mcq":
            options = get_mcq_options(q)
            if not options:
                c.setFont("Helvetica-Oblique", 10)
                c.drawString(q_left + 14, y, "(MCQ options not provided)")
                y -= 14; c.setLineWidth(1.0)
                c.rect(q_box_left, y - 36, q_box_right - q_box_left, 36)
                # Save box coords for MCQ
                save_box(i, q_box_left, y - 36, q_box_right - q_box_left, 36, PAGE_NUM)
                y -= 36 + POST_BOX_GAP
                continue
            labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            mcq_top_y = y
            for idx, opt in enumerate(options):
                label = labels[idx] if idx < len(labels) else str(idx + 1)
                y = draw_mcq_option(label, opt, y)
            # Save MCQ region as box
            save_box(i, q_box_left, y, q_box_right - q_box_left, mcq_top_y - y, PAGE_NUM)
            y -= POST_MCQ_GAP
        else:
            box_h = BOX_HEIGHTS.get(answer_type, 48)
            y = ensure_space(y, box_h + POST_BOX_GAP)
            draw_answer_box(q_box_left, y, q_box_right - q_box_left, box_h, answer_type)
            # ── Save box coords ──
            save_box(i, q_box_left, y - box_h, q_box_right - q_box_left, box_h, PAGE_NUM)
            y -= box_h + POST_BOX_GAP

    for rb in reference_boxes:
        box_size = normalize_answer_type(rb.get("size","medium"))
        if box_size not in BOX_HEIGHTS: box_size = "medium"
        linked_question = str(rb.get("linked_question","") or "").strip()
        y -= Q_GAP - 2
        y = draw_reference_box(box_size, linked_question, y)

    c.save()
    # Commit box coords to DB after PDF is built
    if db is not None:
        try: db.commit()
        except Exception as e: print(f"[PDF] DB commit for box coords failed: {e}")

    return filename