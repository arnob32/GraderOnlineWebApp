// auth.js — all JS extracted from auth.html, zero changes to logic.

function setMode(m) {
  document.getElementById('loginBlock').style.display  = m === 'login'  ? 'block' : 'none';
  document.getElementById('signupBlock').style.display = m === 'signup' ? 'block' : 'none';
  document.querySelectorAll('.mode-btn').forEach(function(b, i) {
    b.classList.toggle('on', (m === 'login' && i === 0) || (m === 'signup' && i === 1));
  });
}

function switchLoginTab(r) {
  document.getElementById('lTabS').classList.toggle('on', r === 'student');
  document.getElementById('lTabT').classList.toggle('on', r === 'teacher');
  document.getElementById('loginRole').value = r;
}

function switchSignupTab(r) {
  document.getElementById('sTabS').classList.toggle('on', r === 'student');
  document.getElementById('sTabT').classList.toggle('on', r === 'teacher');
  document.getElementById('stuForm').style.display = r === 'student' ? 'block' : 'none';
  document.getElementById('tchForm').style.display = r === 'teacher' ? 'block' : 'none';
}

function togglePwd(id, btn) {
  var i = document.getElementById(id);
  if (!i) return;
  if (i.type === 'password') {
    i.type = 'text';
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
  } else {
    i.type = 'password';
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  }
}

var drawerOpen = false;
function toggleDrawer() {
  drawerOpen = !drawerOpen;
  document.getElementById('navDrawer').classList.toggle('open', drawerOpen);
  document.getElementById('hamBtn').classList.toggle('open', drawerOpen);
}

document.addEventListener('click', function(e) {
  var ham    = document.getElementById('hamBtn');
  var drawer = document.getElementById('navDrawer');
  if (drawerOpen && !ham.contains(e.target) && !drawer.contains(e.target)) {
    drawerOpen = false;
    drawer.classList.remove('open');
    ham.classList.remove('open');
  }
});

// Pre-fill login tab from Jinja — window.PREFILL_ROLE set inline in HTML
var pr = window.PREFILL_ROLE || 'student';
if (pr === 'teacher') switchLoginTab('teacher');