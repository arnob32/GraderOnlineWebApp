"""
Train the ExamScanner classifier.
Usage:  python -m app.ExamScanner.train --generate 50
"""
import os, sys, re, json, argparse
from collections import Counter

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "training_data.json")
sys.path.insert(0, os.path.dirname(BASE_DIR))

def build_samples(paths):
    import pytesseract
    from app.ExamScanner.extractor import load_pages, preprocess, ocr_header
    samples = []
    for path in paths:
        try:
            for img in load_pages(path):
                gray = preprocess(img)
                text = ocr_header(gray)
                m    = re.search(r"\b(\d{6,12})\b", text)
                sid  = m.group(1) if m else ""
                data = pytesseract.image_to_data(
                    gray[:int(gray.shape[0]*.25),:],
                    config="--psm 6 --oem 3",
                    output_type=pytesseract.Output.DICT)
                n = len(data["text"])
                for i in range(n):
                    w = data["text"][i].strip()
                    if not w or int(data["conf"][i]) < 15: continue
                    nxt = next((data["text"][j].strip()
                                for j in range(i+1,min(i+3,n))
                                if data["text"][j].strip()),"")
                    samples.append({"text":w,"word":w,"next_word":nxt,
                                    "label":"student_id" if w==sid else "noise"})
        except Exception as e:
            print(f"  skip {path}: {e}")
    return samples

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--generate", type=int, default=0)
    args = p.parse_args()

    if args.generate:
        from app.ExamScanner.extractor import generate_exam_pages
        paths = generate_exam_pages(os.path.join(BASE_DIR,"Generated"), args.generate)
        new   = build_samples(paths)
        old   = json.load(open(DATA_PATH)) if os.path.exists(DATA_PATH) else []
        json.dump(old+new, open(DATA_PATH,"w"), indent=2)
        print(f"  {len(old+new)} samples saved")

    if not os.path.exists(DATA_PATH):
        print("No data — run: python -m app.ExamScanner.train --generate 50"); sys.exit(1)

    data = json.load(open(DATA_PATH))
    print(f"  Samples: {len(data)}  {dict(Counter(s['label'] for s in data))}")
    if len(data) < 20: print("Need >= 20 samples"); sys.exit(1)

    from app.ExamScanner.classifier import FieldClassifier
    clf = FieldClassifier()
    clf.train(DATA_PATH)
    clf.save()

if __name__ == "__main__":
    main()