// ═══════════════════════════════════════════════════════════════════
// GRADING STAMP SYSTEM v4 — Option C
// - Cover page locked (no tools)
// - Tools only inside answer boxes
// - Circled marks in right margin
// - Comment bubbles below answer box
// - Tick/Cross inside answer box
// - One mark per question (editable)
// ═══════════════════════════════════════════════════════════════════

var gradeData = {};    // { qnum: {score, max, comment, tick, cross, page} }
var stampLayer = null;
var coverLock  = null;
var _isCoverPage = false;

// ── Helpers ───────────────────────────────────────────────────────
function savGrades() {
  try { localStorage.setItem('grades_'+SUB_ID, JSON.stringify(gradeData)); } catch(e) {}
}
function loadGrades() {
  try {
    var d = localStorage.getItem('grades_'+SUB_ID);
    if (d) gradeData = JSON.parse(d);
  } catch(e) { gradeData = {}; }
}

function getCurPage() {
  return (typeof curPage !== 'undefined') ? curPage : 1;
}

function getQuestions() {
  if (typeof questions !== 'undefined' && Array.isArray(questions)) return questions;
  return [];
}

function getBoxForQuestion(q) {
  return {
    x:    parseFloat(q.box_x    || q.boxX    || 0),
    y:    parseFloat(q.box_y    || q.boxY    || 0),
    w:    parseFloat(q.box_w    || q.boxW    || 0),
    h:    parseFloat(q.box_h    || q.boxH    || 0),
    page: parseInt(  q.box_page || q.boxPage || 2)
  };
}

function isInBox(nx, ny, box, canvasW, canvasH) {
  if (!box.w || !box.h) return false;
  var bx = box.x / canvasW, by = 1 - (box.y + box.h) / canvasH;
  var bw = box.w / canvasW, bh = box.h / canvasH;
  return nx >= bx && nx <= bx+bw && ny >= by && ny <= by+bh;
}

function findQuestionAtClick(nx, ny, page) {
  var ac = document.getElementById('annotationCanvas');
  if (!ac) return null;
  var cw = ac.width, ch = ac.height;
  var qs = getQuestions();
  for (var i = 0; i < qs.length; i++) {
    var q = qs[i];
    var box = getBoxForQuestion(q);
    if (box.page !== page) continue;
    if (isInBox(nx, ny, box, cw, ch)) return q;
  }
  return null;
}

// ── Cover page lock ───────────────────────────────────────────────
function initStampLayer() {
  var cc = document.getElementById('canvasContainer');
  if (!cc) return;
  if (!stampLayer) {
    stampLayer = document.createElement('div');
    stampLayer.id = 'grade-stamp-layer';
    stampLayer.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:25;overflow:visible;';
    cc.appendChild(stampLayer);
  }
  if (!coverLock) {
    coverLock = document.createElement('div');
    coverLock.id = 'cover-lock';
    coverLock.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;background:rgba(248,245,240,0.85);z-index:30;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;pointer-events:all;border-radius:3px;';
    coverLock.innerHTML = '<div style="font-size:32px;">🔒</div><div style="font-size:13px;font-weight:600;color:#6b7280;">Cover page — marking not allowed</div><div style="font-size:11px;color:#9ca3af;">Go to the answer pages to grade</div>';
    cc.appendChild(coverLock);
  }
}

function updateCoverLock(page) {
  _isCoverPage = (page === 1);
  if (!coverLock) return;
  coverLock.style.display = _isCoverPage ? 'flex' : 'none';
  // Also disable annotation canvas on cover
  var ac = document.getElementById('annotationCanvas');
  if (ac) ac.style.pointerEvents = _isCoverPage ? 'none' : '';
}

// ── Render grade overlays for current page ────────────────────────
function renderGradesForPage(page) {
  if (!stampLayer) return;
  stampLayer.innerHTML = '';
  if (_isCoverPage) return;

  var ac = document.getElementById('annotationCanvas');
  if (!ac) return;
  var cw = ac.width, ch = ac.height;
  var qs = getQuestions();

  qs.forEach(function(q) {
    var qnum = String(q.number || q.question_number);
    var box  = getBoxForQuestion(q);
    var gd   = gradeData[qnum];
    if (!gd || box.page !== page) return;

    // Box position in canvas coords
    var bx = box.x;
    var by = ch - box.y - box.h;  // PDF y is from bottom
    var bw = box.w;
    var bh = box.h;

    // ── Tick/Cross inside answer box ──────────────────────────────
    if (gd.tick || gd.cross) {
      var sym = document.createElement('div');
      var symChar = gd.tick ? '✓' : '✗';
      var symColor = gd.tick ? '#16a34a' : '#dc2626';
      sym.style.cssText = 'position:absolute;left:'+(bx+4)+'px;top:'+(by+2)+'px;color:'+symColor+';font-size:16px;font-weight:900;line-height:1;text-shadow:0 1px 3px rgba(0,0,0,0.15);pointer-events:none;';
      sym.textContent = symChar;
      stampLayer.appendChild(sym);
    }

    // ── Circled score in right margin ─────────────────────────────
    if (gd.score !== null && gd.score !== undefined) {
      var pct = gd.max > 0 ? gd.score / gd.max : 0;
      var circleColor = pct >= 0.8 ? '#16a34a' : pct >= 0.5 ? '#d97706' : '#dc2626';
      var midY = by + bh / 2;

      var circle = document.createElement('div');
      circle.style.cssText = 'position:absolute;right:-38px;top:'+(midY-14)+'px;width:28px;height:28px;border-radius:50%;border:2px solid '+circleColor+';background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;pointer-events:all;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,0.15);';
      circle.innerHTML = '<div style="font-size:7px;font-weight:800;color:'+circleColor+';line-height:1.1;text-align:center;">'+gd.score+'/'+gd.max+'</div>';
      circle.title = 'Click to edit Q'+qnum+' mark';
      circle.addEventListener('click', (function(q_) { return function(e) {
        e.stopPropagation();
        showGradePopup(q_, page);
      };})(q));
      stampLayer.appendChild(circle);
    }

    // ── Comment bubble below answer box ──────────────────────────
    if (gd.comment && gd.comment.trim()) {
      var pct2 = gd.max > 0 ? gd.score / gd.max : 0;
      var bgColor = pct2 >= 0.8 ? '#f0fdf4' : pct2 >= 0.5 ? '#fef9c3' : '#fef2f2';
      var bdColor = pct2 >= 0.8 ? '#86efac' : pct2 >= 0.5 ? '#fde047' : '#fca5a5';
      var txColor = pct2 >= 0.8 ? '#166534' : pct2 >= 0.5 ? '#854d0e' : '#991b1b';
      var bubbleY = by + bh + 4;

      var bubble = document.createElement('div');
      bubble.style.cssText = 'position:absolute;left:'+(bx+6)+'px;top:'+bubbleY+'px;background:'+bgColor+';border:0.5px solid '+bdColor+';border-radius:6px;padding:3px 8px;font-size:10px;font-weight:600;color:'+txColor+';max-width:'+(cw-bx-50)+'px;word-break:break-word;pointer-events:all;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,0.1);';
      bubble.textContent = gd.comment;
      bubble.title = 'Click to edit comment';
      bubble.addEventListener('click', (function(q_) { return function(e) {
        e.stopPropagation();
        showGradePopup(q_, page);
      };})(q));

      // Triangle pointer
      var tri = document.createElement('div');
      tri.style.cssText = 'position:absolute;top:-5px;left:10px;width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:6px solid '+bdColor+';';
      bubble.appendChild(tri);
      stampLayer.appendChild(bubble);
    }
  });
}

// ── Bake grades to annotation canvas ─────────────────────────────
function bakeGradesToCanvas(page) {
  var ac = document.getElementById('annotationCanvas');
  if (!ac) return;
  var ctx = ac.getContext('2d');
  var cw = ac.width, ch = ac.height;
  var qs = getQuestions();

  qs.forEach(function(q) {
    var qnum = String(q.number || q.question_number);
    var box  = getBoxForQuestion(q);
    var gd   = gradeData[qnum];
    if (!gd || box.page !== page) return;

    var bx = box.x, by = ch - box.y - box.h, bw = box.w, bh = box.h;
    var pct = gd.max > 0 ? gd.score / gd.max : 0;
    var color = pct >= 0.8 ? '#16a34a' : pct >= 0.5 ? '#d97706' : '#dc2626';
    var midY = by + bh / 2;

    ctx.save();

    // Tick or Cross inside box
    if (gd.tick || gd.cross) {
      ctx.font = 'bold 18px sans-serif';
      ctx.fillStyle = gd.tick ? '#16a34a' : '#dc2626';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillText(gd.tick ? '\u2713' : '\u2717', bx+5, by+3);
    }

    // Circled score in right margin
    if (gd.score !== null && gd.score !== undefined) {
      var cx2 = cw - 18, cy2 = midY, r = 14;
      ctx.beginPath();
      ctx.arc(cx2, cy2, r, 0, Math.PI*2);
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.fill();
      ctx.fillStyle = color;
      ctx.font = 'bold 8px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(gd.score+'/'+gd.max, cx2, cy2);
    }

    // Comment bubble below box
    if (gd.comment && gd.comment.trim()) {
      var bgC = pct >= 0.8 ? '#f0fdf4' : pct >= 0.5 ? '#fef9c3' : '#fef2f2';
      var bdC = pct >= 0.8 ? '#86efac' : pct >= 0.5 ? '#fde047' : '#fca5a5';
      var txC = pct >= 0.8 ? '#166534' : pct >= 0.5 ? '#854d0e' : '#991b1b';
      var bubY = by + bh + 4;
      var bubW = Math.min(bw - 10, 200), bubH = 18, bubX = bx + 6;

      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(bubX, bubY, bubW, bubH, 5);
      else ctx.rect(bubX, bubY, bubW, bubH);
      ctx.fillStyle = bgC; ctx.fill();
      ctx.strokeStyle = bdC; ctx.lineWidth = 0.7; ctx.stroke();

      // Triangle
      ctx.beginPath();
      ctx.moveTo(bubX+10, bubY);
      ctx.lineTo(bubX+5, bubY-5);
      ctx.lineTo(bubX+16, bubY);
      ctx.closePath();
      ctx.fillStyle = bgC; ctx.fill();
      ctx.strokeStyle = bdC; ctx.lineWidth = 0.7; ctx.stroke();

      ctx.fillStyle = txC;
      ctx.font = '9px sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      var txt = gd.comment.length > 35 ? gd.comment.slice(0,33)+'...' : gd.comment;
      ctx.fillText(txt, bubX+7, bubY+9);
    }

    ctx.restore();
  });
}

// ── Grade popup ───────────────────────────────────────────────────
function removeGradePopup() {
  var p = document.getElementById('grade-popup');
  var b = document.getElementById('grade-backdrop');
  if (p) p.remove();
  if (b) b.remove();
}

function showGradePopup(q, page) {
  removeGradePopup();
  var qnum = String(q.number || q.question_number);
  var maxM = q.max || q.max_marks || q.marks || '?';
  var existing = gradeData[qnum] || {};

  var bd = document.createElement('div');
  bd.id = 'grade-backdrop';
  bd.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.3);z-index:9998;';
  bd.addEventListener('click', removeGradePopup);

  var pop = document.createElement('div');
  pop.id = 'grade-popup';
  pop.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border-radius:14px;padding:22px;z-index:9999;box-shadow:0 8px 40px rgba(0,0,0,0.25);min-width:300px;border:1px solid #e2e8f0;font-family:inherit;';
  pop.addEventListener('click', function(e){e.stopPropagation();});

  var existTick  = existing.tick  ? 'checked' : '';
  var existCross = existing.cross ? 'checked' : '';
  var existScore = existing.score !== undefined ? existing.score : '';
  var existComment = existing.comment || '';

  pop.innerHTML =
    '<div style="font-weight:800;font-size:15px;margin-bottom:4px;color:#0f172a;">Grade Q'+qnum+'</div>'+
    '<div style="font-size:11px;color:#2563eb;margin-bottom:16px;">Max marks: '+maxM+'</div>'+
    '<div style="margin-bottom:14px;">'+
      '<label style="font-size:11px;font-weight:700;color:#64748b;display:block;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em;">Mark</label>'+
      '<div style="display:flex;align-items:center;gap:8px;">'+
        '<input id="gp-score" type="number" min="0" max="'+maxM+'" step="0.5" value="'+existScore+'" placeholder="0" '+
          'style="flex:1;padding:10px;border:1px solid #e2e8f0;border-radius:8px;font-size:20px;font-weight:800;font-family:monospace;text-align:center;outline:none;">'+
        '<span style="font-size:16px;color:#64748b;white-space:nowrap;">/ '+maxM+'</span>'+
      '</div>'+
    '</div>'+
    '<div style="margin-bottom:14px;">'+
      '<label style="font-size:11px;font-weight:700;color:#64748b;display:block;margin-bottom:8px;text-transform:uppercase;letter-spacing:.04em;">Mark on paper</label>'+
      '<div style="display:flex;gap:10px;">'+
        '<label style="display:flex;align-items:center;gap:6px;cursor:pointer;padding:8px 12px;border:1px solid #e2e8f0;border-radius:8px;flex:1;background:#f0fdf4;">'+
          '<input type="radio" name="gp-sym" id="gp-tick" value="tick" '+existTick+' style="accent-color:#16a34a;">'+
          '<span style="font-size:18px;color:#16a34a;font-weight:900;">✓</span>'+
          '<span style="font-size:12px;font-weight:600;color:#166534;">Tick</span>'+
        '</label>'+
        '<label style="display:flex;align-items:center;gap:6px;cursor:pointer;padding:8px 12px;border:1px solid #e2e8f0;border-radius:8px;flex:1;background:#fef2f2;">'+
          '<input type="radio" name="gp-sym" id="gp-cross" value="cross" '+existCross+' style="accent-color:#dc2626;">'+
          '<span style="font-size:18px;color:#dc2626;font-weight:900;">✗</span>'+
          '<span style="font-size:12px;font-weight:600;color:#991b1b;">Cross</span>'+
        '</label>'+
        '<label style="display:flex;align-items:center;gap:6px;cursor:pointer;padding:8px 12px;border:1px solid #e2e8f0;border-radius:8px;flex:1;background:#f8fafc;">'+
          '<input type="radio" name="gp-sym" id="gp-none" value="none" '+((!existTick&&!existCross)?'checked':'')+'>'+
          '<span style="font-size:12px;font-weight:600;color:#64748b;">None</span>'+
        '</label>'+
      '</div>'+
    '</div>'+
    '<div style="margin-bottom:18px;">'+
      '<label style="font-size:11px;font-weight:700;color:#64748b;display:block;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em;">Comment</label>'+
      '<textarea id="gp-comment" rows="2" placeholder="Add feedback for this answer..." '+
        'style="width:100%;padding:9px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;font-family:inherit;resize:none;outline:none;box-sizing:border-box;">'+existComment+'</textarea>'+
    '</div>'+
    '<div style="display:flex;gap:8px;">'+
      '<button onclick="removeGradePopup()" style="flex:1;padding:10px;border:1px solid #e2e8f0;border-radius:8px;background:#f8fafc;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;">Cancel</button>'+
      (existing.score !== undefined ?
        '<button id="gp-clear" style="padding:10px 14px;border:1px solid #fca5a5;border-radius:8px;background:#fef2f2;color:#991b1b;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;">Clear</button>' : '')+
      '<button id="gp-ok" style="flex:2;padding:10px;border:none;border-radius:8px;background:#2563eb;color:#fff;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;">Save Mark ✓</button>'+
    '</div>';

  // Clear button
  var clearBtn = pop.querySelector('#gp-clear');
  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      delete gradeData[qnum];
      savGrades();
      renderGradesForPage(page);
      updateRightPanel();
      removeGradePopup();
    });
  }

  // Save button
  pop.querySelector('#gp-ok').addEventListener('click', function() {
    var sv = pop.querySelector('#gp-score').value.trim();
    if (!sv) { pop.querySelector('#gp-score').style.borderColor='#dc2626'; pop.querySelector('#gp-score').focus(); return; }
    var score = parseFloat(sv);
    var sym = pop.querySelector('input[name="gp-sym"]:checked');
    var symVal = sym ? sym.value : 'none';
    var comment = pop.querySelector('#gp-comment').value.trim();

    gradeData[qnum] = {
      score:   score,
      max:     parseFloat(maxM) || 0,
      tick:    symVal === 'tick',
      cross:   symVal === 'cross',
      comment: comment,
      page:    page
    };
    savGrades();
    renderGradesForPage(page);
    updateRightPanel();
    removeGradePopup();
    // Auto-advance right panel to next question
    if (typeof questions !== 'undefined') {
      var idx = questions.findIndex(function(q2){return String(q2.number||q2.question_number)===qnum;});
      if (idx >= 0 && idx < questions.length-1) {
        var nextQ = questions[idx+1];
        var nextNum = String(nextQ.number||nextQ.question_number);
        // Highlight next question in right panel
        document.querySelectorAll('.qblock').forEach(function(b){
          var n = b.querySelector('.qnum');
          if (n && n.textContent.trim() === nextNum) b.click && b.click();
        });
      }
    }
  });

  document.body.appendChild(bd);
  document.body.appendChild(pop);
  setTimeout(function(){var el=pop.querySelector('#gp-score');if(el)el.focus();el.select&&el.select();},100);
}

// ── Update right panel scores ─────────────────────────────────────
function updateRightPanel() {
  var total = 0, maxTotal = 0;
  Object.values(gradeData).forEach(function(gd) {
    total    += parseFloat(gd.score)||0;
    maxTotal += parseFloat(gd.max)||0;
  });
  // Update score display
  var awEl  = document.getElementById('dispAw');
  var pctEl = document.getElementById('dispPct');
  if (awEl && Object.keys(gradeData).length > 0) awEl.textContent = total;
  if (pctEl && maxTotal > 0) pctEl.textContent = Math.round((total/maxTotal)*100)+'%';

  // Update individual question inputs in right panel
  Object.keys(gradeData).forEach(function(qnum) {
    var gd = gradeData[qnum];
    document.querySelectorAll('.qblock').forEach(function(block) {
      var numEl = block.querySelector('.qnum');
      if (numEl && numEl.textContent.trim() === qnum) {
        var inp = block.querySelector('.pts-inp');
        if (inp && inp.value !== String(gd.score)) {
          inp.value = gd.score;
          inp.dispatchEvent(new Event('input',{bubbles:true}));
          inp.dispatchEvent(new Event('change',{bubbles:true}));
        }
      }
    });
  });
  setTimeout(function(){
    if (typeof updateTotals==='function') updateTotals();
    if (typeof refreshProgress==='function') refreshProgress();
  },100);
}

// ── Canvas click handler ──────────────────────────────────────────
function initGradeClick() {
  var ac = document.getElementById('annotationCanvas');
  if (!ac) { setTimeout(initGradeClick, 600); return; }

  ac.addEventListener('click', function(e) {
    if (_isCoverPage) return;
    if (!activeTool) return;
    var stampTools = ['mark-stamp','comment-stamp','tick-stamp','cross-stamp'];
    if (stampTools.indexOf(activeTool) < 0) return;

    e.stopPropagation();
    var rect = ac.getBoundingClientRect();
    var nx = (e.clientX - rect.left) / ac.width;
    var ny = (e.clientY - rect.top)  / ac.height;
    var page = getCurPage();

    var q = findQuestionAtClick(nx, ny, page);
    if (q) {
      showGradePopup(q, page);
    } else {
      // Show hint
      showHint('Click inside an answer box to grade it');
    }
  });
}

function showHint(msg) {
  var h = document.getElementById('grade-hint');
  if (!h) {
    h = document.createElement('div');
    h.id = 'grade-hint';
    h.style.cssText = 'position:fixed;bottom:70px;left:50%;transform:translateX(-50%);background:#0f172a;color:#fff;padding:8px 16px;border-radius:100px;font-size:12px;font-weight:600;z-index:9999;pointer-events:none;transition:opacity .3s;';
    document.body.appendChild(h);
  }
  h.textContent = msg;
  h.style.opacity = '1';
  clearTimeout(window._hintTimer);
  window._hintTimer = setTimeout(function(){h.style.opacity='0';}, 2500);
}

// ── Bake all + save before finish ────────────────────────────────
function hookFinishBtn() {
  var btn = document.getElementById('btnFinish');
  if (!btn) { setTimeout(hookFinishBtn, 600); return; }
  btn.addEventListener('click', function(e) {
    var hasGrades = Object.keys(gradeData).length > 0;
    if (!hasGrades) return;
    e.stopImmediatePropagation();
    e.preventDefault();
    btn.disabled = true;
    btn.textContent = 'Saving marks to paper…';

    var pages = {};
    Object.values(gradeData).forEach(function(gd) {
      if (gd.page) pages[gd.page] = true;
    });
    var pageList = Object.keys(pages).map(Number);
    var idx = 0;

    function doNext() {
      if (idx >= pageList.length) {
        gradeData = {};
        localStorage.removeItem('grades_'+SUB_ID);
        try {
          var stored = JSON.parse(localStorage.getItem('anno_'+SUB_ID)||'{}');
          pageList.forEach(function(p){delete stored[p];});
          localStorage.setItem('anno_'+SUB_ID, JSON.stringify(stored));
        } catch(e2) {}
        if (stampLayer) stampLayer.innerHTML = '';
        btn.disabled = false;
        btn.textContent = 'Finish Marking';
        if (typeof finishMarking === 'function') finishMarking();
        return;
      }
      var pg = pageList[idx];
      if (typeof renderPage === 'function') {
        renderPage(pg).then(function() {
          setTimeout(function() {
            bakeGradesToCanvas(pg);
            var ac = document.getElementById('annotationCanvas');
            if (ac && typeof annotations !== 'undefined') {
              annotations[pg] = ac.toDataURL('image/png');
            }
            if (typeof _autoSavePageToServer === 'function') {
              _autoSavePageToServer(pg).then(function() {
                idx++; setTimeout(doNext, 500);
              });
            } else {
              if (typeof _scheduleAutoSave === 'function') _scheduleAutoSave(pg);
              idx++; setTimeout(doNext, 900);
            }
          }, 400);
        });
      } else {
        bakeGradesToCanvas(pg);
        idx++; setTimeout(doNext, 800);
      }
    }
    doNext();
  }, true);
}

// ── Hook page render ──────────────────────────────────────────────
function hookPageRender() {
  if (typeof renderPage === 'function') {
    var orig = renderPage;
    window.renderPage = function(page) {
      var r = orig.apply(this, arguments);
      var doUpdate = function() {
        updateCoverLock(page);
        renderGradesForPage(page);
      };
      if (r && typeof r.then === 'function') r.then(function(){ setTimeout(doUpdate, 400); });
      else setTimeout(doUpdate, 400);
      return r;
    };
  } else {
    setTimeout(hookPageRender, 400);
  }
}

// ── Answer box highlight when tool active ─────────────────────────
function highlightAnswerBoxes(show) {
  var existing = document.querySelectorAll('.ans-box-highlight');
  existing.forEach(function(el) { el.remove(); });
  if (!show || !stampLayer) return;

  var ac = document.getElementById('annotationCanvas');
  if (!ac) return;
  var cw = ac.width, ch = ac.height;
  var page = getCurPage();
  var qs = getQuestions();

  qs.forEach(function(q) {
    var box = getBoxForQuestion(q);
    if (box.page !== page || !box.w) return;
    var bx = box.x, by = ch - box.y - box.h, bw = box.w, bh = box.h;
    var hl = document.createElement('div');
    hl.className = 'ans-box-highlight';
    hl.style.cssText = 'position:absolute;left:'+bx+'px;top:'+by+'px;width:'+bw+'px;height:'+bh+'px;border:2px dashed #2563eb;border-radius:3px;background:rgba(37,99,235,0.04);pointer-events:none;z-index:20;';
    stampLayer.appendChild(hl);
  });
}

// ── Monkey-patch selectTool to highlight boxes ────────────────────
function hookSelectTool() {
  if (typeof selectTool !== 'function') { setTimeout(hookSelectTool, 500); return; }
  var origSel = selectTool;
  window.selectTool = function(tool) {
    origSel.apply(this, arguments);
    var stampTools = ['mark-stamp','comment-stamp','tick-stamp','cross-stamp'];
    var isStamp = stampTools.indexOf(tool) >= 0;
    highlightAnswerBoxes(isStamp && activeTool !== null);
  };
}

// ── Init ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  loadGrades();
  initStampLayer();
  initGradeClick();
  hookPageRender();
  hookFinishBtn();
  hookSelectTool();
  setTimeout(function() {
    updateCoverLock(getCurPage());
    renderGradesForPage(getCurPage());
    updateRightPanel();
  }, 2000);
});