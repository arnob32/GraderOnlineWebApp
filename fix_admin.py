content = open('app/templates/Admin/marking_overview.html', encoding='utf-8', errors='replace').read()

old = '${r.status || "\u2014"}'
new = '${r.percentage != null ? (r.percentage >= 50 ? "Pass" : "Fail") : (r.status || "\u2014")}'

if old in content:
    content = content.replace(old, new)
    open('app/templates/Admin/marking_overview.html', 'w', encoding='utf-8').write(content)
    print('Fixed')
else:
    print('Not found')
    idx = content.find('r.status')
    print(repr(content[max(0,idx-30):idx+60]))
