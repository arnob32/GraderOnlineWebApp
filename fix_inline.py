content = open('app/routes/exam_routes.py', encoding='utf-8', errors='replace').read()
# Change download endpoint to serve inline (for iframe preview)
old = 'return FileResponse(\n        path=pdf_path,\n        media_type="application/pdf",\n        filename=safe_name,\n        headers={"Content-Disposition": f\'attachment; filename="{safe_name}"\'},\n    )'
new = 'return FileResponse(\n        path=pdf_path,\n        media_type="application/pdf",\n        filename=safe_name,\n        headers={"Content-Disposition": f\'inline; filename="{safe_name}"\'},\n    )'
if old in content:
    content = content.replace(old, new)
    open('app/routes/exam_routes.py', 'w', encoding='utf-8').write(content)
    print("Fixed - PDF serves inline")
else:
    print("Not found")
    idx = content.find("Content-Disposition")
    print(repr(content[max(0,idx-50):idx+100]))
