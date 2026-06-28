import os, re
import cv2, numpy as np, pytesseract, fitz

for _p in [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
]:
    if os.path.isfile(_p):
        pytesseract.pytesseract.tesseract_cmd = _p
        break

def load_pages(path, dpi=150):
    if path.endswith(".pdf"):
        doc, mat = fitz.open(path), fitz.Matrix(dpi/72, dpi/72)
        imgs = []
        for p in doc:
            px  = p.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            arr = np.frombuffer(px.samples, np.uint8).reshape(px.height, px.width, 3)
            imgs.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
        doc.close(); return imgs
    img = cv2.imread(path)
    return [img] if img is not None else []

def preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    pts  = np.column_stack(np.where(gray < 200))
    if len(pts) > 100:
        a = cv2.minAreaRect(pts)[-1]
        if a < -45: a += 90
        if abs(a) > 0.3:
            h, w = gray.shape
            gray = cv2.warpAffine(gray, cv2.getRotationMatrix2D((w/2,h/2),a,1), (w,h))
    h, w = gray.shape
    if w < 2000:
        gray = cv2.resize(gray, (2400, int(h*2400/w)), interpolation=cv2.INTER_LANCZOS4)
    return gray

def ocr_header(gray, frac=0.20):
    roi = gray[:int(gray.shape[0]*frac), :]
    return pytesseract.image_to_string(roi, config="--psm 6 --oem 3")

def parse_fields(text):
    text = re.sub(r"[ \t]+", " ", text)
    f    = {}
    # Inner page: "7200001, Lastname, Firstname   Page 2 of 4"
    m = re.search(r"(\d{6,12})\s*[,.]\s*([A-Za-z].{2,40}?)\s+[Pp]age\s+(\d+)\s+of\s+(\d+)", text)
    if m:
        f["student_id"]  = m.group(1)
        f["name"]        = m.group(2).strip().rstrip(".,")
        f["page_number"] = m.group(3)
        f["total_pages"] = m.group(4)
        return f
    # Cover page: "Student-ID: 7200001" + "Name: Lastname, Firstname"
    m = re.search(r"[Ss]tudent[\s\-]?[Ii][Dd]\s*[:\-]\s*(\d{6,12})", text)
    if m: f["student_id"] = m.group(1)
    m = re.search(r"[Nn]ame\s*[:\-]\s*([A-Za-z][A-Za-z0-9\s,\-]{2,50})", text)
    if m: f["name"] = m.group(1).strip().rstrip(".,")
    if "student_id" not in f:
        m = re.search(r"\b(\d{7,12})\b", text)
        if m: f["student_id"] = m.group(1)
    m = re.search(r"[Pp]age\s+(\d+)\s+of\s+(\d+)", text)
    if m: f["page_number"] = m.group(1); f["total_pages"] = m.group(2)
    return f

def extract_fields(img_input):
    if isinstance(img_input, str):
        pages = load_pages(img_input)
        if not pages: return {"error": f"Cannot load: {img_input}"}
        img_input = pages[0]
    return parse_fields(ocr_header(preprocess(img_input)))

def confidence_score(f):
    w = {"student_id":.5,"name":.3,"page_number":.1,"total_pages":.1}
    return round(sum(v for k,v in w.items() if f.get(k)), 3)

def merge_pages(lst):
    out = {}
    for f in lst:
        for k,v in f.items():
            if v and k not in out: out[k] = v
    return out

def scan_image(path, out_dir=""):
    pages = load_pages(path)
    if not pages: return {"error": f"Cannot load: {path}"}
    fields = merge_pages([parse_fields(ocr_header(preprocess(p))) for p in pages])
    return {"filename": os.path.basename(path), "fields": fields,
            "student_id": fields.get("student_id",""),
            "name":       fields.get("name",""),
            "page_number":fields.get("page_number",""),
            "confidence": confidence_score(fields)}

def generate_exam_pages(out_dir, count=50):
    import random
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rlc
    os.makedirs(out_dir, exist_ok=True)
    first = ["Raju","Priya","Hans","Maria","Arjun","Sita"]
    last  = ["Naidu","Kumar","Müller","Schmidt","Sharma","Patel"]
    used, paths = set(), []
    def uid():
        while True:
            s = str(random.randint(7000001,9999999))
            if s not in used: used.add(s); return s
    for n in range(count):
        fn,ln,sid = random.choice(first),random.choice(last),uid()
        total = random.randint(2,4)
        for pg in range(1, total+1):
            pdf = os.path.join(out_dir, f"exam_{n+1:03d}_p{pg}.pdf")
            W,H = A4; c = rlc.Canvas(pdf, pagesize=A4)
            c.setFont("Courier", 12)
            if pg == 1:
                c.drawString(50, H-60, f"Student-ID: {sid}")
                c.drawString(50, H-80, f"Name: {ln}, {fn}")
            else:
                c.drawString(50, H-55, f"{sid}, {ln}, {fn}    Page {pg} of {total}")
            c.save(); paths.append(pdf)
    return paths

print("[ExamScanner] extractor.py loaded")