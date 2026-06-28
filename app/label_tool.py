def confidence_level(s):
    return "high" if s>=0.85 else "medium" if s>=0.65 else "low" if s>=0.45 else "unmatched"

def format_result(fields, conf):
    return {"student_code": fields.get("student_id",""),
            "student_name": fields.get("name",""),
            "page_number":  fields.get("page_number",""),
            "confidence":   round(conf,3),
            "level":        confidence_level(conf),
            "auto_assign":  conf >= 0.65,
            "needs_review": 0.45 <= conf < 0.65}