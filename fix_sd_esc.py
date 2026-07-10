p = open('app/templates/Teacher/student_directory.html', encoding='utf-8', errors='replace').read()

# Add safeEsc function that won't conflict with layout's esc
old = "var allPapers = [], statusFilter = '';"
new = "var allPapers = [], statusFilter = ''; function safeEsc(s){return String(s==null?'':s).replace(/[<>]/g,function(c){return c=='<'?'&lt;':'&gt;'});}"

p = p.replace(old, new)

# Replace esc( with safeEsc( in renderTable function only
for term in ['esc(p.student_name','esc(p.student_code','esc(p.exam_title',
             'esc(p.subject_name','esc(grade)','esc(p.student_email',
             'esc(p.file_url','esc(p.download_url','esc(p.student_code||','esc(p.student_name||']:
    p = p.replace(term, term.replace('esc(', 'safeEsc('))

print('Has safeEsc:', 'safeEsc' in p)
print('Has loadPapers:', 'loadPapers' in p)

open('app/templates/Teacher/student_directory.html', 'w', encoding='utf-8').write(p)
print('Fixed')