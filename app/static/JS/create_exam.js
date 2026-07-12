// create_exam.js — all logic extracted from create_exam.html

let questionCount = 0;
let _examSubmitting = false;  // guard against double submission

const QUESTION_TYPE_META = {
  veryShort: { label:'Very Short',            submitValue:'small',    hint:'Compact one-line answer area.' },
  small:     { label:'Small',                 submitValue:'small',    hint:'Short descriptive response.' },
  medium:    { label:'Medium',                submitValue:'medium',   hint:'Standard theory answer area.' },
  essay:     { label:'Essay',                 submitValue:'large',    hint:'Long-form essay answer.' },
  large:     { label:'Large',                 submitValue:'large',    hint:'Extended lined answer space.' },
  fullPage:  { label:'Full Page',             submitValue:'fullPage', hint:'Full-page answer area.' },
  mcq:       { label:'Multiple Choice (MCQ)', submitValue:'mcq',      hint:'Structured MCQ with lettered options.' },
  diagram:   { label:'Diagram Space',         submitValue:'diagram',  hint:'Blank drawing area for diagrams.' },
};

window.addEventListener('load', () => {
  const sname = document.getElementById('preSubjectName')?.value || '';
  const scode = document.getElementById('courseCode')?.value     || '';
  const ssem  = document.getElementById('semester')?.value       || '';

  document.getElementById('lp-subject-name').textContent = sname ? decodeURIComponent(sname) : '(no subject)';
  document.getElementById('lp-subject-code').textContent = scode || '—';
  document.getElementById('lp-semester').textContent     = ssem  ? `Semester ${ssem}` : '—';

  addQuestion();
  updateBar();

  const tmInput = document.getElementById('totalMarks');
  if (tmInput) tmInput.addEventListener('input', () => updateBar());
});

function toggleSection(hd) {
  hd.classList.toggle('open');
  hd.nextElementSibling?.classList.toggle('open');
}

function updateBar() {
  const title    = document.getElementById('examTitle')?.value.trim() || 'Untitled Exam';
  const totalRaw = parseInt(document.getElementById('totalMarks')?.value) || 0;
  const cards    = document.querySelectorAll('.qcard');
  let used = 0;
  cards.forEach(c => { used += parseInt(c.querySelector('.question-marks')?.value) || 0; });

  const _bt = document.getElementById('barTitle');  if (_bt) _bt.textContent = title;
  const _bq = document.getElementById('barQCount'); if (_bq) _bq.textContent = `${cards.length} question${cards.length !== 1 ? 's' : ''}`;
  const _bm = document.getElementById('barMarks');  if (_bm) _bm.textContent = `${used} / ${totalRaw || '—'} Marks`;

  document.getElementById('lp-exam-title').textContent = title;
  document.getElementById('lp-exam-sub').textContent   = totalRaw ? `${totalRaw} marks total` : 'Set total marks';
  document.getElementById('h-used').textContent   = used;
  document.getElementById('h-total').textContent  = totalRaw || '—';
  document.getElementById('h-qcount').textContent = cards.length;

  const lpUsed  = document.getElementById('lp-marks-used');
  const lpTotal = document.getElementById('lp-marks-total');
  if (lpUsed)  lpUsed.textContent  = used;
  if (lpTotal) lpTotal.textContent = totalRaw || '—';

  const pct = totalRaw ? Math.min(100, Math.round(used / totalRaw * 100)) : 0;
  document.getElementById('h-progress').style.width = pct + '%';

  const empty = document.getElementById('emptyQ');
  if (empty) empty.style.display = cards.length ? 'none' : 'block';
}

function buildAnswerTypeOptions() {
  return `<option value="">— Select type —</option>` +
    Object.entries(QUESTION_TYPE_META).map(([k, v]) =>
      `<option value="${k}">${v.label}</option>`).join('');
}

function buildMcqRows(id, count = 4) {
  return 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.slice(0, count).split('').map(l => `
    <div class="mcq-opt-row">
      <div class="mcq-opt-letter">${l}</div>
      <input type="text" class="mcq-opt-input" placeholder="Option ${l}" oninput="syncMcq(${id})">
    </div>`).join('');
}

function addQuestion(prefill = null) {
  questionCount++;
  const id = questionCount;

  const html = `
  <div class="qcard" id="q-${id}" data-id="${id}">
    <div class="qcard-hd">
      <div class="qnum-badge" id="qnum-${id}">Q${id}</div>
      <div class="qcard-title-preview" id="qtitle-${id}">Enter your question…</div>
      <div class="qcard-actions">
        <div class="qa-btn" title="Attach image" onclick="document.getElementById('qimg-inp-${id}').click()">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21,15 16,10 5,21"/></svg>
        </div>
        <div class="qa-btn del" title="Remove question" onclick="removeQuestion(${id})">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>
        </div>
      </div>
    </div>
    <div class="qcard-body">
      <textarea class="q-textarea" id="qtext-${id}"
        placeholder="Enter your question here…&#10;e.g. Explain the fundamental principles of…"
        oninput="onQTextInput(${id})"></textarea>
      <div class="attach-row">
        <label class="attach-lbl">
          <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
          Attach Image
          <input type="file" id="qimg-inp-${id}" class="question-image" accept="image/*" onchange="onImgChange(${id},event)">
        </label>
        <span class="attach-hint-txt">Optional — graph, diagram, chart or visual prompt</span>
      </div>
      <div class="img-preview-wrap" id="img-wrap-${id}">
        <img id="img-prev-${id}" alt="Preview">
        <button type="button" class="img-rm" onclick="removeImg(${id})">Remove image</button>
      </div>
      <div class="q-meta">
        <div>
          <span class="qm-label">Question Level</span>
          <div class="sel-wrap">
            <select class="qm-sel question-level" onchange="onLevelChange(${id})">
              <option value="main">Main Question</option>
              <option value="sub">Sub Question</option>
            </select>
          </div>
          <div class="q-type-hint" id="lvl-hint-${id}">Use Main Question for standalone questions or parent headings like Q8.</div>
          <div class="group-note" id="group-note-${id}">Parent question — add marks &amp; answer boxes to sub-questions below.</div>
        </div>
        <div class="qa-config">
          <span class="qm-label">Answer Type</span>
          <div class="sel-wrap">
            <select class="qm-sel answer-type" onchange="onTypeChange(${id})">${buildAnswerTypeOptions()}</select>
          </div>
          <div class="q-type-hint" id="type-hint-${id}">Choose the most suitable answer area.</div>
        </div>
        <div class="qa-config">
          <span class="qm-label">Marks</span>
          <input type="number" class="qm-input question-marks" placeholder="e.g. 10" min="1" oninput="updateBar()">
        </div>
      </div>
      <div class="mcq-box" id="mcq-${id}">
        <div class="mcq-box-hd">
          <div>
            <div class="mcq-box-title">MCQ Options</div>
            <div class="mcq-box-sub">Enter option text — letters are added automatically in the PDF.</div>
          </div>
          <div class="mcq-actions">
            <button type="button" class="mcq-mini-btn" onclick="addMcqOpt(${id})">+ Add Option</button>
            <button type="button" class="mcq-mini-btn" onclick="resetMcq(${id})">Reset</button>
          </div>
        </div>
        <div class="mcq-options-list" id="mcq-grid-${id}">${buildMcqRows(id, 4)}</div>
        <textarea class="mcq-hidden" id="mcq-hidden-${id}"></textarea>
      </div>
    </div>
  </div>`;

  document.getElementById('questionsContainer').insertAdjacentHTML('beforeend', html);
  renumber();
  updateBar();

  if (prefill) {
    const card = document.getElementById(`q-${id}`);
    if (prefill.text)  { document.getElementById(`qtext-${id}`).value = prefill.text; onQTextInput(id); }
    if (prefill.marks)   card.querySelector('.question-marks').value = prefill.marks;
    if (prefill.level)   card.querySelector('.question-level').value = prefill.level;
    if (prefill.type)  { card.querySelector('.answer-type').value = prefill.type; onTypeChange(id); }
    if (prefill.options) setMcqOpts(id, prefill.options);
    renumber(); updateBar();
  }
}

function onQTextInput(id) {
  const txt     = document.getElementById(`qtext-${id}`)?.value?.trim();
  const preview = document.getElementById(`qtitle-${id}`);
  if (preview) preview.textContent = txt || 'Enter your question…';
}

function removeQuestion(id) {
  document.getElementById(`q-${id}`)?.remove();
  renumber(); updateBar();
}

function getQuestionCards() { return [...document.querySelectorAll('.qcard')]; }

function questionHasSubquestions(card) {
  let sib = card.nextElementSibling;
  while (sib && sib.classList.contains('qcard')) {
    const lvl = sib.querySelector('.question-level')?.value || 'main';
    if (lvl === 'main') return false;
    if (lvl === 'sub')  return true;
    sib = sib.nextElementSibling;
  }
  return false;
}

function computeHierarchy() {
  const cards = getQuestionCards();
  let mainIdx = 0, subIdx = 0;
  return cards.map(card => {
    const level = card.querySelector('.question-level')?.value || 'main';
    if (level === 'sub') {
      if (!mainIdx) mainIdx = 1;
      return { card, level, number: `${mainIdx}.${++subIdx}` };
    }
    subIdx = 0;
    return { card, level: 'main', number: `${++mainIdx}` };
  });
}

function renumber() {
  computeHierarchy().forEach(({ card, level, number }) => {
    const id = card.dataset.id;
    const badge = document.getElementById(`qnum-${id}`);
    if (badge) badge.textContent = `Q${number}`;
    const isGroupParent = level === 'main' && questionHasSubquestions(card);
    card.dataset.groupParent = isGroupParent ? 'true' : 'false';
    card.querySelectorAll('.qa-config').forEach(el => el.style.display = isGroupParent ? 'none' : '');
    const gn = document.getElementById(`group-note-${id}`);
    if (gn) gn.style.display = isGroupParent ? 'block' : 'none';
    const lh = document.getElementById(`lvl-hint-${id}`);
    if (lh) lh.textContent = isGroupParent
      ? 'Parent heading — add marks on sub-questions below.'
      : (level === 'sub'
        ? 'Numbered under the latest main question e.g. Q8.1, Q8.2.'
        : 'Use Main Question for standalone questions or parent headings.');
    if (!isGroupParent) onTypeChange(id);
  });
}

function onLevelChange(id) { renumber(); updateBar(); }

function onTypeChange(id) {
  const card = document.getElementById(`q-${id}`);
  if (!card) return;
  const val = card.querySelector('.answer-type')?.value;
  const isGroupParent = card.dataset.groupParent === 'true';
  const mcqBox = document.getElementById(`mcq-${id}`);
  if (mcqBox) mcqBox.style.display = (!isGroupParent && val === 'mcq') ? 'block' : 'none';
  const hint = document.getElementById(`type-hint-${id}`);
  if (hint) hint.textContent = QUESTION_TYPE_META[val]?.hint || 'Choose the most suitable answer area.';
  if (val === 'mcq') syncMcq(id);
}

function onImgChange(id, event) {
  const file = event.target.files?.[0];
  const wrap = document.getElementById(`img-wrap-${id}`);
  const img  = document.getElementById(`img-prev-${id}`);
  if (!file || !file.type.startsWith('image/')) { if (wrap) wrap.style.display = 'none'; return; }
  const r = new FileReader();
  r.onload = e => { img.src = e.target.result; wrap.style.display = 'block'; };
  r.readAsDataURL(file);
}

function removeImg(id) {
  const inp  = document.getElementById(`qimg-inp-${id}`);
  const wrap = document.getElementById(`img-wrap-${id}`);
  const img  = document.getElementById(`img-prev-${id}`);
  if (inp)  inp.value = '';
  if (img)  img.removeAttribute('src');
  if (wrap) wrap.style.display = 'none';
}

function addMcqOpt(id) {
  const grid = document.getElementById(`mcq-grid-${id}`);
  if (!grid) return;
  const count  = grid.querySelectorAll('.mcq-opt-row').length;
  const letter = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[count] || String(count + 1);
  const row    = document.createElement('div');
  row.className = 'mcq-opt-row';
  row.innerHTML = `<div class="mcq-opt-letter">${letter}</div>
    <input type="text" class="mcq-opt-input" placeholder="Option ${letter}" oninput="syncMcq(${id})">`;
  grid.appendChild(row);
}

function resetMcq(id) {
  const grid = document.getElementById(`mcq-grid-${id}`);
  if (grid) grid.innerHTML = buildMcqRows(id, 4);
  syncMcq(id);
}

function syncMcq(id) {
  const grid = document.getElementById(`mcq-grid-${id}`);
  if (!grid) return;
  const vals   = [...grid.querySelectorAll('.mcq-opt-input')].map(i => i.value.trim()).filter(Boolean);
  const hidden = document.getElementById(`mcq-hidden-${id}`);
  if (hidden) hidden.value = vals.join('\n');
}

function setMcqOpts(id, opts) {
  const grid = document.getElementById(`mcq-grid-${id}`);
  if (!grid) return;
  grid.innerHTML = buildMcqRows(id, Math.max(4, opts.length));
  grid.querySelectorAll('.mcq-opt-input').forEach((inp, i) => { if (opts[i]) inp.value = opts[i]; });
  syncMcq(id);
}

function buildExamFormData() {
  const title      = document.getElementById('examTitle').value.trim();
  const totalMarks = parseInt(document.getElementById('totalMarks').value, 10);
  const subject    = document.getElementById('subject').value    || '';
  const courseCode = document.getElementById('courseCode').value || '';
  const deptId     = document.getElementById('departmentId').value || '';
  const semesterRaw = document.getElementById('semesterId')?.value
                   || document.getElementById('semester')?.value || '0';
  const semester   = String(parseInt(semesterRaw) || 0);
  const teacherId  = document.getElementById('teacherId').value || '0';

  if (!title)      { showToast('Exam Title is required.', 'warn'); return null; }
  if (!totalMarks) { showToast('Total Marks is required.', 'warn'); return null; }

  const qCards = document.querySelectorAll('.qcard');
  if (!qCards.length) { showToast('Add at least one question.', 'warn'); return null; }

  const questions = [];
  const fd = new FormData();
  let marksSum = 0;
  const hierarchy = computeHierarchy();

  for (let i = 0; i < qCards.length; i++) {
    const card = qCards[i];
    const meta = hierarchy[i];
    const id   = card.dataset.id;
    const text = document.getElementById(`qtext-${id}`)?.value.trim();
    const level = card.querySelector('.question-level')?.value || 'main';
    const isGroup  = level === 'main' && questionHasSubquestions(card);
    const marksRaw = card.querySelector('.question-marks')?.value;
    const marks    = parseInt(marksRaw) || 0;
    const uiType   = card.querySelector('.answer-type')?.value;
    const type     = QUESTION_TYPE_META[uiType]?.submitValue || uiType || '';
    const imgFile  = document.getElementById(`qimg-inp-${id}`)?.files?.[0];

    if (!text) { showToast(`Fill question text for Q${meta.number}`, 'warn'); return null; }

    const q = { number: meta.number, text, level, has_subquestions: isGroup, is_group_parent: isGroup, has_image: !!imgFile };

    if (!isGroup) {
      if (!marks || !type) { showToast(`Answer type and marks required for Q${meta.number}`, 'warn'); return null; }
      q.marks = marks; q.answer_type = type; marksSum += marks;
      if (type === 'mcq') {
        const opts = document.getElementById(`mcq-hidden-${id}`)?.value.trim();
        if (!opts) { showToast(`MCQ options required for Q${meta.number}`, 'warn'); return null; }
        q.mcq_options = opts;
      }
    } else { q.marks = 0; q.answer_type = 'group'; }

    if (imgFile) fd.append(`question_image_${i + 1}`, imgFile);
    questions.push(q);
  }

  if (marksSum !== totalMarks) {
    if (!confirm(`Marks used (${marksSum}) does not equal Total Marks (${totalMarks}). Continue anyway?`)) return null;
  }

  fd.append('title',                   title);
  fd.append('course_code',             courseCode);
  fd.append('subject',                 subject);
  fd.append('total_marks',             String(totalMarks));
  fd.append('department_id',           deptId || '0');
  fd.append('semester',                semester || '0');
  fd.append('teacher_id',              teacherId);
  fd.append('cover_page_enabled',      'false');
  fd.append('cover_title',             'Exam Instructions');
  fd.append('cover_rules',             document.getElementById('coverRules')?.value.trim() || '');
  fd.append('cover_show_student_name', 'true');
  fd.append('cover_show_student_id',   'true');
  fd.append('questions_json',          JSON.stringify(questions));
  fd.append('reference_boxes_json',    '[]');
  fd.append('exam_date_time',          '');
  fd.append('description',             '');

  const excelInput = document.getElementById('studentListFile');
  if (excelInput && excelInput.files && excelInput.files.length > 0) {
    fd.append('student_list_file', excelInput.files[0]);
  }

  return { fd, title };
}

async function submitExam(mode = 'preview') {
  // Guard against double submission
  if (_examSubmitting) {
    console.warn('[ExamCreate] Already submitting, ignoring duplicate call');
    return;
  }
  _examSubmitting = true;

  const payload = buildExamFormData();
  if (!payload) { _examSubmitting = false; return; }
  const { fd, title } = payload;

  const btn      = document.getElementById(mode === 'preview' ? 'previewBtn' : 'generateBtn');
  const idleHtml = btn?.innerHTML || '';
  if (btn) { btn.disabled = true; btn.textContent = mode === 'preview' ? 'Preparing…' : 'Generating…'; }
  showToast(mode === 'preview' ? 'Preparing preview…' : 'Generating PDF…');

  if (mode === 'preview') fd.append('preview_only', 'true');
  try {
    const res = await fetch('/api/exams/create', { method: 'POST', body: fd });
    if (!res.ok) {
      let detail = `Server error ${res.status}`;
      try { const e = await res.json(); detail = e.detail || detail; } catch (_) {}
      showToast(detail, 'err'); return;
    }
    const data = await res.json();
    if (!data.success || !data.pdf_url) { showToast('No PDF returned.', 'err'); return; }

    const fname = (title || 'exam').replace(/[<>:"/\\|?*]/g, '').trim() + '.pdf';
    if (mode === 'preview') {
      const canvas = document.getElementById('previewCanvas');
      const frame  = document.getElementById('previewFrame');
      const dl     = document.getElementById('previewDL');
      const status = document.getElementById('previewStatusText');
      frame.src = data.pdf_url; dl.href = data.pdf_url; dl.download = fname;
      if (status) status.textContent = `Loaded ${fname}`;
      canvas.classList.add('show');
      canvas.scrollIntoView({ behavior: 'smooth', block: 'start' });
      showToast(`Preview ready — ${data.students_count} student(s).`, 'ok');
    } else {
      // Download all PDFs as a single ZIP file
      const examId  = data.exam_id;
      const zipUrl  = `/api/exams/download-zip/${examId}`;
      const zipName = (title || 'exam').replace(/[<>:"/\\|?*]/g, '').trim() + '_all_papers.zip';
      const a = document.createElement('a');
      a.href = zipUrl; a.download = zipName; a.style.display = 'none';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      showToast(`${data.pdfs_generated} PDF(s) ready — downloading as ZIP.`, 'ok');
    }
  } catch (err) {
    console.error(err); showToast('Network error.', 'err');
  } finally {
    _examSubmitting = false;
    if (btn) { btn.disabled = false; btn.innerHTML = idleHtml; }
  }
}

function previewExam()  { submitExam('preview');  }
function generateExam() { submitExam('generate'); }

function hidePreview() {
  document.getElementById('previewCanvas').classList.remove('show');
  document.getElementById('previewFrame').src = '';
  const s = document.getElementById('previewStatusText');
  if (s) s.textContent = 'No preview loaded yet';
}

function showTemplateToast() {
  showToast('Templates coming soon — pre-built exam structures in the next release.', '');
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = 'toast show' + (type ? ' ' + type : '');
  clearTimeout(window._tt);
  window._tt = setTimeout(() => t.classList.remove('show'), 3200);
}

function toggleCoverOptions() {}
function renderSubjects()    {}
function renderCourseCodes() {}