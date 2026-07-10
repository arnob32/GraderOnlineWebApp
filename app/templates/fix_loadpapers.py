content = open('app/templates/Teacher/student_directory.html', encoding='utf-8', errors='replace').read()

# Find and replace loadPapers function
old = """function loadPapers() {
  try {
    // Data pre-loaded from server
    allPapers = window._papersData || [];
    updateStats(); applyFilters();
  } catch(e) {
    document.getElementById('tableBody').innerHTML = '<div class=\"empty-state\"><h3>Error: '+e.message+'</h3></div>';
  }
}"""

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

if old in content:
    content = content.replace(old, new)
    open('app/templates/Teacher/student_directory.html', 'w', encoding='utf-8').write(content)
    print('Fixed - loadPapers now uses fetch API')
else:
    print('Pattern not found')
    idx = content.find('function loadPapers')
    if idx >= 0:
        print('Found at:', idx)
        print(repr(content[idx:idx+300]))
    else:
        print('loadPapers not found at all')