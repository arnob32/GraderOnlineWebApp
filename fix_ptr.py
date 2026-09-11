content = open('app/static/JS/grading_dashboard.js', encoding='utf-8', errors='replace').read()
old = 'function setPointerEvents(tool) {\n  const active = !!tool;'
new = 'function setPointerEvents(tool) {\n  const _st=["mark-stamp","comment-stamp","tick-stamp","cross-stamp"];\n  const active = !!tool || _st.includes(activeTool);'
if old in content:
    content = content.replace(old, new)
    open('app/static/JS/grading_dashboard.js', 'w', encoding='utf-8').write(content)
    print('Fixed')
else:
    print('Not found')
