content = open('app/static/JS/create_exam.js', encoding='utf-8', errors='replace').read()
# Add preview=true to formdata when in preview mode
old = "  try {\n    const res = await fetch('/api/exams/create', { method: 'POST', body: fd });"
new = "  if (mode === 'preview') fd.append('preview_only', 'true');\n  try {\n    const res = await fetch('/api/exams/create', { method: 'POST', body: fd });"
if old in content:
    content = content.replace(old, new)
    open('app/static/JS/create_exam.js', 'w', encoding='utf-8').write(content)
    print('Fixed')
else:
    print('Not found')
