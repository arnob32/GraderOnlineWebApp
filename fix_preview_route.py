content = open('app/routes/exam_routes.py', encoding='utf-8', errors='replace').read()
old = "    student_list_file:    UploadFile = File(None),"
new = "    student_list_file:    UploadFile = File(None),\n    preview_only:         str        = Form(\"\"),"
if old in content:
    content = content.replace(old, new)
    # Limit to 1 student for preview
    old2 = "    if not students_entries:\n        raise HTTPException(404,"
    new2 = "    if preview_only == 'true':\n        students_entries = students_entries[:1]\n    if not students_entries:\n        raise HTTPException(404,"
    content = content.replace(old2, new2)
    open('app/routes/exam_routes.py', 'w', encoding='utf-8').write(content)
    print('Fixed')
else:
    print('Not found')
