p = open('app/templates/Teacher/student_directory.html', encoding='utf-8', errors='replace').read()

p = p.replace(
    "var allPapers = [], statusFilter = '';",
    "var allPapers = [], statusFilter = ''; console.log('SD script loaded');"
)
p = p.replace(
    "window.onload=loadPapers;",
    "window.onload=function(){console.log('onload fired');try{loadPapers();}catch(e){alert('JS ERROR: '+e.message);}}"
)

open('app/templates/Teacher/student_directory.html', 'w', encoding='utf-8').write(p)
print('done')