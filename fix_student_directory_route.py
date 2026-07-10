# This patches the student_directory_page route to pass data directly to template
# so it doesn't need the JS API call at all

content = open('app/routes/marking_routes.py', encoding='utf-8', errors='replace').read()

old = '''@router.get("/student-directory", response_class=HTMLResponse)
def student_directory_page(request: Request, db: Session = Depends(get_db)):
    redir = _require_teacher(request)
    if redir: return redir
    from app.models.exam import Exam
    from app.models.subject import Subject
    tid     = marking_service.session_teacher(request)
    exams_q = db.query(Exam)
    if tid:
        exams_q = exams_q.filter(Exam.teacher_id == int(tid))
    return templates.TemplateResponse("Teacher/student_directory.html", {
        "request":  request,
        "subjects": db.query(Subject).order_by(Subject.name).all(),
        "exams":    exams_q.order_by(Exam.title).all(),
    })'''

new = '''@router.get("/student-directory", response_class=HTMLResponse)
def student_directory_page(request: Request, db: Session = Depends(get_db)):
    redir = _require_teacher(request)
    if redir: return redir
    from app.models.exam import Exam
    from app.models.subject import Subject
    import json
    tid     = marking_service.session_teacher(request)
    exams_q = db.query(Exam)
    if tid:
        exams_q = exams_q.filter(Exam.teacher_id == int(tid))

    # Pre-load submissions data for the template
    from app.models.student import Student
    from app.models.mark import Mark
    subs = db.query(Submission).order_by(Submission.id.desc()).all()
    papers = []
    for sub in subs:
        exam    = db.get(Exam, sub.exam_id) if sub.exam_id else None
        student = db.get(Student, sub.student_id) if sub.student_id else None
        subject = (db.get(Subject, exam.subject_id)
                   if exam and getattr(exam, "subject_id", None) else None)
        mark    = db.query(Mark).filter(Mark.submission_id == sub.id).first()
        if tid and exam and getattr(exam, "teacher_id", None) and exam.teacher_id != int(tid):
            continue
        name = ""
        if student:
            if hasattr(student, "first_name") and student.first_name:
                name = f"{student.first_name} {student.last_name or ''}".strip()
            else:
                name = getattr(student, "name", "") or ""
        papers.append({
            "submission_id": sub.id,
            "exam_id":       sub.exam_id,
            "exam_title":    exam.title if exam else f"Exam #{sub.exam_id}",
            "subject_id":    getattr(exam, "subject_id", None) if exam else None,
            "subject_name":  subject.name if subject else "",
            "student_id":    sub.student_id,
            "student_name":  name or f"Student #{sub.student_id}",
            "student_code":  getattr(student, "student_code", "") if student else "",
            "student_email": getattr(student, "email", "") if student else "",
            "status":        sub.status or "uploaded",
            "score":         getattr(mark, "score",        None) if mark else None,
            "max_score":     getattr(mark, "max_score",    None) if mark else None,
            "percentage":    getattr(mark, "percentage",   None) if mark else None,
            "letter_grade":  getattr(mark, "letter_grade", "") if mark else "",
            "file_url":      f"/uploads/open-submission/{sub.id}",
            "download_url":  f"/uploads/download-annotated-pdf/{sub.id}",
            "grade_url":     f"/uploads/grade-submission/{sub.id}",
        })

    return templates.TemplateResponse("Teacher/student_directory.html", {
        "request":        request,
        "subjects":       db.query(Subject).order_by(Subject.name).all(),
        "exams":          exams_q.order_by(Exam.title).all(),
        "papers_json":    json.dumps(papers),
    })'''

if old in content:
    content = content.replace(old, new)
    open('app/routes/marking_routes.py', 'w', encoding='utf-8').write(content)
    print('Fixed - data now passed directly to template')
else:
    print('Pattern not found')
    idx = content.find('student-directory", response_class')
    print(repr(content[idx:idx+200]))