import pathlib

path = pathlib.Path('app/templates/Teacher/student_directory.html')
content = path.read_text(encoding='utf-8', errors='replace')

# Add Send Email button after the Send button in renderTable
old = "            ? '<button class=\"btn-send\" onclick=\"sendOne(' + p.submission_id + ',this)\">Send</button>'"

new = "            ? '<button class=\"btn-send\" onclick=\"sendOne(' + p.submission_id + ',this)\">Send</button>' + '<button class=\"btn-view\" onclick=\"sendEmail(' + p.submission_id + ',\\''+esc(p.student_email||'')+'\\')\">✉ Email</button>'"

if old in content:
    content = content.replace(old, new)
    print('Added email button')
else:
    print('Pattern not found - searching...')
    idx = content.find('btn-send')
    print(repr(content[idx:idx+200]))

# Add sendEmail function before window.onload
old2 = 'window.onload = loadPapers;'
new2 = '''async function sendEmail(submId, email) {
  if (!submId) return;
  var label = email ? ' to ' + email : '';
  if (!confirm('Send result email' + label + '?')) return;
  try {
    var r = await fetch('/results-tools/submission/' + submId + '/send-email', {method:'POST'});
    var d = await r.json();
    showToast(d.message || 'Email sent', d.ok ? 'success' : 'error');
  } catch(e) { showToast(e.message, 'error'); }
}
window.onload = loadPapers;'''

if old2 in content:
    content = content.replace(old2, new2)
    print('Added sendEmail function')
else:
    print('window.onload not found')

path.write_text(content, encoding='utf-8')
print('Saved')