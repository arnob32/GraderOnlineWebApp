content = open('app/templates/Teacher/student_directory.html', encoding='utf-8', errors='replace').read()
idx = content.find('function loadPapers')
end = content.find('\n}', idx) + 2
old = content[idx:end]
new = """async function loadPapers() {
  var body = document.getElementById('tableBody');
  try {
    var r = await fetch('/api/student-directory');
    if (!r.ok) { body.innerHTML = '<div style=\"padding:20px;color:red\">API error: '+r.status+'</div>'; return; }
    var data = await r.json();
    allPapers = Array.isArray(data) ? data : (data.submissions || data.results || []);
    updateStats();
    applyFilters();
  } catch(e) {
    body.innerHTML = '<div style=\"padding:20px;color:red\">Load error: '+e.message+'</div>';
  }
}"""
content = content[:idx] + new + content[end:]
open('app/templates/Teacher/student_directory.html', 'w', encoding='utf-8').write(content)
print('Fixed')
