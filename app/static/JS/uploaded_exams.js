// uploaded_exams.js

var allFiles = [], statusFilter = '', markCache = {};

async function loadFiles() {
  show('loadingState'); hide('errorState'); hide('emptyState'); hide('groupedView');
  try {
    var res  = await fetch('/uploads/uploaded-exams-data');
    if (!res.ok) throw new Error('Server error ' + res.status);
    var data = await res.json();
    allFiles = Array.isArray(data.files) ? data.files : [];
    hide('loadingState');
    await fetchMarkData();
    populateFilters();
    updateStats();
    applyFilters();
  } catch(err) {
    hide('loadingState'); show('errorState');
    var em = document.getElementById('errorMsg');
    if (em) em.textContent = err.message;
  }
}

async function fetchMarkData() {
  var toCheck = allFiles.filter(function(f){ return f.submission_id > 0; });
  await Promise.allSettled(toCheck.map(async function(f) {
    try {
      var r = await fetch('/marking/' + f.submission_id);
      if (r.ok) {
        var m = await r.json();
        markCache[f.submission_id] = m;
        if (m.status) f.status = m.status;
      }
    } catch(_) {}
  }));
}

function populateFilters() {
  var subjects = {}, semesters = {};
  allFiles.forEach(function(f) {
    if (f.subject_name) subjects[f.subject_id] = f.subject_name + (f.subject_code ? ' (' + f.subject_code + ')' : '');
    if (f.semester)     semesters[f.semester]  = 'Semester ' + f.semester;
  });
  var sf   = document.getElementById('subjectFilter');
  var semf = document.getElementById('semesterFilter');
  while (sf.options.length > 1)   sf.remove(1);
  while (semf.options.length > 1) semf.remove(1);
  Object.entries(subjects).forEach(function(e) {
    var o = document.createElement('option'); o.value = e[0]; o.textContent = e[1]; sf.appendChild(o);
  });
  Object.entries(semesters).sort(function(a,b){ return Number(a[0])-Number(b[0]); }).forEach(function(e) {
    var o = document.createElement('option'); o.value = e[0]; o.textContent = e[1]; semf.appendChild(o);
  });
}

function updateStats() {
  var total    = allFiles.length;
  var pending  = allFiles.filter(function(f){ return ['uploaded','assigned','sent_for_marking'].includes(f.status); }).length;
  var graded   = allFiles.filter(function(f){ return ['marked','locked','reviewed'].includes(f.status); }).length;
  var released = allFiles.filter(function(f){ return f.status === 'returned'; }).length;
  var totalKb  = allFiles.reduce(function(s,f){ return s + (Number(f.size_kb)||0); }, 0);
  var sizeStr  = totalKb >= 1024 ? (totalKb/1024).toFixed(1)+' MB' : totalKb.toFixed(1)+' KB';
  var _s = function(id,v){ var el=document.getElementById(id); if(el) el.textContent=v; };
  _s('statTotal',total); _s('statPending',pending); _s('statGraded',graded);
  _s('statReleased',released); _s('statSize',sizeStr);
}

function setStatusTab(btn, status) {
  document.querySelectorAll('.filter-tab').forEach(function(b){ b.classList.remove('active'); });
  btn.classList.add('active'); statusFilter = status; applyFilters();
}

function applyFilters() {
  var q      = document.getElementById('searchInput').value.toLowerCase().trim();
  var subjId = document.getElementById('subjectFilter').value;
  var semId  = document.getElementById('semesterFilter').value;
  var list = allFiles.filter(function(f) {
    var matchQ    = !q      || [f.student_name,f.exam_title,f.filename].join(' ').toLowerCase().includes(q);
    var matchSubj = !subjId || String(f.subject_id) === String(subjId);
    var matchSem  = !semId  || String(f.semester) === String(semId);
    var matchSt   = !statusFilter || f.status === statusFilter;
    return matchQ && matchSubj && matchSem && matchSt;
  });
  var count = document.getElementById('tableCount');
  if (count) count.textContent = list.length + ' paper' + (list.length!==1?'s':'');
  if (!list.length) { show('emptyState'); hide('groupedView'); return; }
  hide('emptyState'); show('groupedView');
  renderGrouped(list);
}

function renderGrouped(files) {
  var groups = {};
  files.forEach(function(f) {
    var sk = String(f.subject_id || 'none');
    var sm = String(f.semester   || 0);
    if (!groups[sk]) groups[sk] = { subject_name: f.subject_name || 'No Subject', subject_code: f.subject_code || '', semesters: {} };
    if (!groups[sk].semesters[sm]) groups[sk].semesters[sm] = [];
    groups[sk].semesters[sm].push(f);
  });
  var view = document.getElementById('groupedView');
  view.innerHTML = Object.entries(groups).map(function(entry) {
    var grp = entry[1];
    var totalInSubj = Object.values(grp.semesters).reduce(function(s,a){ return s+a.length; }, 0);
    var semSections = Object.entries(grp.semesters)
      .sort(function(a,b){ return Number(a[0])-Number(b[0]); })
      .map(function(se) {
        var sem = se[0], papers = se[1];
        var semLabel = sem === '0' ? 'No Semester' : 'Semester ' + sem;
        var cards = papers.map(function(f){ return buildCard(f); }).join('');
        return '<div class="sem-section">'
          + '<div class="sem-label">' + esc(semLabel) + ' <span style="font-weight:600;color:var(--text-muted);">— ' + papers.length + ' paper' + (papers.length!==1?'s':'') + '</span></div>'
          + '<div class="cards-grid">' + cards + '</div>'
          + '</div>';
      }).join('');
    return '<div class="subject-card">'
      + '<div class="subject-card-header"><div>'
      + '<div class="subject-card-title">' + esc(grp.subject_name) + '</div>'
      + '<div class="subject-card-meta">'
      + (grp.subject_code ? '<span class="sbadge-blue">' + esc(grp.subject_code) + '</span>' : '')
      + '<span>' + totalInSubj + ' paper' + (totalInSubj!==1?'s':'') + '</span>'
      + '</div></div></div>'
      + semSections + '</div>';
  }).join('');
}

function buildCard(f) {
  var submId    = f.submission_id || 0;
  var status    = f.status || 'uploaded';
  var isReturn  = status === 'returned';
  var gradeUrl  = esc('/uploads/grade-submission/' + submId);
  var mark      = markCache[submId] || null;
  var grade     = mark && mark.letter_grade ? mark.letter_grade : null;
  var gradeClass= grade ? 'g-' + grade : 'g-none';
  var gradeLabel= grade || '—';
  var score  = mark ? Number(mark.score||0)     : 0;
  var maxSc  = mark ? Number(mark.max_score||0) : 0;
  var pct    = mark ? Number(mark.percentage||(maxSc>0?score/maxSc*100:0)) : 0;
  var pctFill= Math.min(100,Math.max(0,pct));
  var scoreStr = maxSc > 0
    ? (Number.isInteger(score)?score:score.toFixed(1)) + ' / ' + (Number.isInteger(maxSc)?maxSc:maxSc.toFixed(1))
    : 'Not graded yet';
  var pctStr = maxSc > 0 ? pct.toFixed(1) + '%' : '';
  var statusLabel = status.replace(/_/g,' ');
  var releaseBtn = '';
  if (isReturn) {
    releaseBtn = '<span class="back-btn released"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>Sent</span>';
  } else if (submId) {
    releaseBtn = '<button class="back-btn" onclick="event.stopPropagation();sendToStudent(' + submId + ',this)"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22 11 13 2 9l20-7z"/></svg>Send</button>';
  }
  return '<div class="card-wrap ' + gradeClass + '" data-submission="' + submId + '">'
    + '<div class="card-inner">'
    + '<div class="card-face card-front">'
    + '<div class="card-banner"><div class="banner-orb"></div>'
    + '<div class="grade-badge">' + esc(gradeLabel) + '</div>'
    + '<div class="banner-status">' + esc(statusLabel) + '</div></div>'
    + '<div class="card-body">'
    + '<div class="card-filename" title="' + esc(f.student_name||f.filename) + '">' + esc(f.student_name||f.filename) + '</div>'
    + '<div class="card-meta-row">'
    + '<span class="card-meta">' + esc(f.exam_title||'') + ' · ' + (Number(f.size_kb)||0).toFixed(1) + ' KB</span>'
    + '<span class="card-pct">' + pctStr + '</span></div>'
    + '<div class="progress-wrap"><div class="progress-fill" style="width:' + pctFill + '%"></div></div>'
    + '</div></div>'
    + '<div class="card-face card-back">'
    + '<div class="back-grade">' + esc(gradeLabel) + '</div>'
    + '<div class="back-filename">' + esc(f.student_name||f.filename) + '</div>'
    + '<div class="back-score">' + esc(scoreStr) + (pctStr?' · '+pctStr:'') + '</div>'
    + '<div class="back-actions">'
    + '<a href="' + gradeUrl + '" class="back-btn" onclick="event.stopPropagation()"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>Grade</a>'
    + releaseBtn
    + '</div></div></div></div>';
}

async function sendToStudent(submId, btn) {
  if (!confirm('Send annotated paper to student? This marks it as returned.')) return;
  btn.disabled = true; btn.textContent = 'Sending...';
  try {
    await fetch('/marking/' + submId + '/lock', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({internal_note:'Sent to student'})
    });
    var res  = await fetch('/marking/' + submId + '/release', {method:'POST'});
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Send failed');
    var f = allFiles.find(function(x){ return x.submission_id === submId; });
    if (f) f.status = 'returned';
    showToast('Paper sent to student');
    setTimeout(function(){ loadFiles(); }, 1200);
  } catch(e) {
    btn.disabled = false; btn.textContent = 'Send';
    showToast(e.message || 'Send failed');
  }
}

function show(id) { var el=document.getElementById(id); if(el) el.style.display=''; }
function hide(id) { var el=document.getElementById(id); if(el) el.style.display='none'; }

function showToast(msg) {
  var c = document.getElementById('toast-container');
  if (!c) return;
  var t = document.createElement('div');
  t.className = 'toast toast-info'; t.textContent = msg;
  c.appendChild(t);
  setTimeout(function(){ t.classList.add('show'); }, 10);
  setTimeout(function(){ t.classList.remove('show');
    setTimeout(function(){ if(c.contains(t)) c.removeChild(t); }, 300); }, 3000);
}

function esc(s) {
  return String(s==null?'':s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

window.onload = loadFiles;