(function () {
  'use strict';
  var KEY = 'marks5_' + SUB_ID;
  var marks = {};
  try { marks = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { marks = {}; }
  var STAMP = ['mark-stamp', 'comment-stamp', 'tick-stamp', 'cross-stamp'];
  var finishing = false;
  var lastSeen = {}, cand = {}, seeded = false;

  function page() { return (typeof curPage !== 'undefined') ? curPage : 1; }
  function cvs() { return document.getElementById('annotationCanvas'); }
  function fmt(n) { return String(Math.round(parseFloat(n) * 100) / 100); }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(marks)); } catch (e) {} }
  function note(m, t) { if (typeof toast === 'function') toast(m, t); }
  function col(p) { return p >= 0.8 ? '#16a34a' : p >= 0.5 ? '#d97706' : '#dc2626'; }
  function bgFor(p) { return p >= 0.8 ? '#dcfce7' : p >= 0.5 ? '#fef3c7' : '#fee2e2'; }
  function numOrNull(x) {
    if (x === null || x === undefined || x === '') return null;
    var v = parseFloat(x);
    return isNaN(v) ? null : v;
  }

  function qlist() {
    var out = [];
    if (typeof questions === 'undefined' || !Array.isArray(questions)) return out;
    questions.forEach(function (q, i) {
      var n = q.number != null ? q.number : q.num != null ? q.num : q.question_number != null ? q.question_number : (i + 1);
      var m = q.max != null ? q.max : q.max_marks != null ? q.max_marks : q.marks != null ? q.marks : 0;
      out.push({ n: String(n), max: parseFloat(m) || 0 });
    });
    return out;
  }

  function persist() {
    try {
      if (typeof saveAnnotationSnap === 'function') saveAnnotationSnap();
      else if (typeof annotations !== 'undefined') annotations[page()] = cvs().toDataURL('image/png');
    } catch (e) { console.warn('[stamps] snap failed', e); }
    try { if (typeof _scheduleAutoSave === 'function') _scheduleAutoSave(page()); } catch (e) {}
  }

  function findBlock(n) {
    var blocks = document.querySelectorAll('.qblock'), target = null, idx = -1;
    qlist().forEach(function (q, i) { if (q.n === String(n)) idx = i; });
    blocks.forEach(function (b) {
      var num = b.querySelector('.qnum');
      if (!target && num && num.textContent.trim() === String(n)) target = b;
    });
    return target || (idx >= 0 ? blocks[idx] : null) || null;
  }

  function markAwarded(n, score) {
    lastSeen[n] = score;
    if (typeof questions === 'undefined' || !Array.isArray(questions)) return;
    qlist().forEach(function (q, i) { if (q.n === String(n) && questions[i]) questions[i].awarded = score; });
  }

  function refreshTotals() {
    ['updateTotals', 'refreshProgress', 'updateProgress', 'checkFinishReady'].forEach(function (fn) {
      try { if (typeof window[fn] === 'function') window[fn](); } catch (e) {}
    });
    var sum = 0, tot = 0, any = false;
    qlist().forEach(function (q, i) {
      var v = numOrNull(questions[i] && questions[i].awarded);
      tot += q.max;
      if (v !== null) { sum += v; any = true; }
    });
    var aw = document.getElementById('dispAw'), pc = document.getElementById('dispPct');
    if (aw && any) aw.textContent = fmt(sum);
    if (pc && tot > 0 && any) pc.textContent = Math.round(sum / tot * 100) + '%';
  }

  function syncPanel(n, score) {
    markAwarded(n, score);
    var target = findBlock(n);
    if (target) {
      var inp = target.querySelector('.pts-inp');
      if (inp) {
        inp.value = score;
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
      var pts = target.querySelector('.qpts');
      if (pts && pts.children.length === 0) pts.textContent = fmt(score);
    }
    refreshTotals();
  }

  function drawMark(ctx, cx, cy, score, max, u) {
    var r = 21 * u, c = col(max > 0 ? score / max : 0);
    ctx.save();
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.fill();
    ctx.lineWidth = 2.5 * u; ctx.strokeStyle = c; ctx.stroke();
    ctx.fillStyle = c; ctx.font = 'bold ' + Math.round(10.5 * u) + 'px Arial';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(fmt(score) + '/' + fmt(max), cx, cy);
    ctx.restore();
    return { x: cx - r - 4 * u, y: cy - r - 4 * u, w: 2 * r + 8 * u, h: 2 * r + 8 * u };
  }
  function drawTick(ctx, cx, cy, u) {
    ctx.save(); ctx.strokeStyle = '#16a34a'; ctx.lineWidth = 4 * u; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.beginPath(); ctx.moveTo(cx - 11 * u, cy); ctx.lineTo(cx - 3 * u, cy + 9 * u); ctx.lineTo(cx + 12 * u, cy - 11 * u); ctx.stroke();
    ctx.restore();
  }
  function drawCross(ctx, cx, cy, u) {
    ctx.save(); ctx.strokeStyle = '#dc2626'; ctx.lineWidth = 4 * u; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(cx - 10 * u, cy - 10 * u); ctx.lineTo(cx + 10 * u, cy + 10 * u);
    ctx.moveTo(cx + 10 * u, cy - 10 * u); ctx.lineTo(cx - 10 * u, cy + 10 * u); ctx.stroke();
    ctx.restore();
  }
  function layout(ctx, text, u) {
    var fs = Math.round(11 * u); ctx.font = fs + 'px Arial';
    var maxW = 170 * u, words = String(text).split(/\s+/), lines = [], cur = '';
    words.forEach(function (w) {
      var t = cur ? cur + ' ' + w : w;
      if (ctx.measureText(t).width > maxW && cur) { lines.push(cur); cur = w; } else cur = t;
    });
    if (cur) lines.push(cur);
    var lh = fs * 1.35, pad = 7 * u, widest = 0;
    lines.forEach(function (l) { widest = Math.max(widest, ctx.measureText(l).width); });
    return { fs: fs, lines: lines, lh: lh, pad: pad, bw: widest + 2 * pad, bh: lines.length * lh + 2 * pad };
  }
  function paintBubble(ctx, L, bx, by, bg, u) {
    ctx.beginPath(); ctx.rect(bx, by, L.bw, L.bh);
    ctx.fillStyle = bg; ctx.fill();
    ctx.lineWidth = u; ctx.strokeStyle = 'rgba(0,0,0,0.25)'; ctx.stroke();
    ctx.fillStyle = '#1a1209'; ctx.font = L.fs + 'px Arial'; ctx.textAlign = 'left'; ctx.textBaseline = 'top';
    L.lines.forEach(function (l, i) { ctx.fillText(l, bx + L.pad, by + L.pad + i * L.lh); });
  }
  function drawComment(ctx, text, cx, cy, bg, u) {
    ctx.save();
    var L = layout(ctx, text, u);
    paintBubble(ctx, L, cx - L.bw / 2, cy - L.bh / 2, bg, u);
    ctx.restore();
  }
  function drawCommentBelow(ctx, text, cx, topY, bg, u) {
    ctx.save();
    var L = layout(ctx, text, u), W = ctx.canvas.width;
    var bx = Math.max(2 * u, Math.min(cx - L.bw / 2, W - L.bw - 2 * u));
    paintBubble(ctx, L, bx, topY, bg, u);
    ctx.restore();
    return { x: bx - u, y: topY - u, w: L.bw + 2 * u, h: L.bh + 2 * u };
  }

  function clearMarkArea(ctx, W, H, m) {
    ctx.clearRect(m.rx * W, m.ry * H, m.rw * W, m.rh * H);
    if (m.crw) ctx.clearRect(m.crx * W, m.cry * H, m.crw * W, m.crh * H);
  }
  function renderMark(ctx, W, H, cx, cy, score, max, comment) {
    var u = W / 700, b = drawMark(ctx, cx, cy, score, max, u);
    var g = { rx: b.x / W, ry: b.y / H, rw: b.w / W, rh: b.h / H, cmt: '' };
    var txt = (comment || '').trim();
    if (txt) {
      var cr = drawCommentBelow(ctx, txt, cx, b.y + b.h + 2 * u, bgFor(max > 0 ? score / max : 0), u);
      g.cmt = txt; g.crx = cr.x / W; g.cry = cr.y / H; g.crw = cr.w / W; g.crh = cr.h / H;
    }
    return g;
  }

  function editPage(pg, fn, done) {
    if (pg === page()) {
      var ac = cvs();
      fn(ac.getContext('2d'), ac.width, ac.height);
      persist();
      if (done) done();
      return;
    }
    var src = (typeof annotations !== 'undefined') ? annotations[pg] : null;
    if (!src) { if (done) done(new Error('no data for page ' + pg)); return; }
    var im = new Image();
    im.onload = function () {
      var c2 = document.createElement('canvas');
      c2.width = im.width; c2.height = im.height;
      var ctx = c2.getContext('2d');
      ctx.drawImage(im, 0, 0);
      fn(ctx, c2.width, c2.height);
      annotations[pg] = c2.toDataURL('image/png');
      try { localStorage.setItem('anno_' + SUB_ID, JSON.stringify(annotations)); } catch (e) {}
      if (typeof _scheduleAutoSave === 'function') _scheduleAutoSave(pg);
      if (done) done();
    };
    im.onerror = function () { if (done) done(new Error('image load failed')); };
    im.src = src;
  }

  function repaintMark(n, score, comment, done) {
    var m = marks[n];
    if (!m) { if (done) done(); return; }
    editPage(m.page, function (ctx, W, H) {
      var cx = (m.rx + m.rw / 2) * W, cy = (m.ry + m.rh / 2) * H;
      clearMarkArea(ctx, W, H, m);
      delete m.crx; delete m.cry; delete m.crw; delete m.crh;
      var g = renderMark(ctx, W, H, cx, cy, score, m.max, comment);
      for (var k in g) m[k] = g[k];
      m.score = score;
    }, function (err) { if (!err) save(); if (done) done(err); });
  }

  function placeMark(n, score, max, nx, ny, comment) {
    var ac = cvs(), ctx = ac.getContext('2d'), W = ac.width, H = ac.height;
    var old = marks[n];
    if (old) clearMarkArea(ctx, W, H, old);
    var g = renderMark(ctx, W, H, nx * W, ny * H, score, max, comment);
    g.score = score; g.max = max; g.page = page();
    marks[n] = g;
    save(); persist(); syncPanel(n, score);
    note('Q' + n + ': ' + fmt(score) + '/' + fmt(max) + ' placed on paper', 'ok');
  }

  function applyFromPanel(n, v, max) {
    var m = marks[n];
    if (!m) return;
    if (v === null) {
      editPage(m.page, function (ctx, W, H) { clearMarkArea(ctx, W, H, m); }, function (err) {
        if (err) { note('Open page ' + m.page + ' once so Q' + n + ' can be updated', 'err'); return; }
        delete marks[n]; save();
      });
      return;
    }
    if (max > 0 && v > max) v = max;
    repaintMark(n, v, m.cmt, function (err) {
      if (err) note('Open page ' + m.page + ' once so Q' + n + ' can be updated', 'err');
    });
  }

  function poll() {
    if (typeof questions === 'undefined' || !Array.isArray(questions)) return;
    var L = qlist();
    if (!L.length) return;
    L.forEach(function (q, i) {
      var cur = numOrNull(questions[i] && questions[i].awarded);
      if (!seeded) { lastSeen[q.n] = cur; return; }
      if (cur === lastSeen[q.n]) { delete cand[q.n]; return; }
      var c3 = cand[q.n];
      if (c3 && c3.v === cur) { c3.k++; } else { cand[q.n] = c3 = { v: cur, k: 1 }; }
      if (c3.k >= 2) {
        lastSeen[q.n] = cur; delete cand[q.n];
        if (marks[q.n]) applyFromPanel(q.n, cur, q.max);
      }
    });
    seeded = true;
  }

  function el(tag, css, txt) {
    var e = document.createElement(tag);
    if (css) e.style.cssText = css;
    if (txt != null) e.textContent = txt;
    return e;
  }
  var INP = 'width:100%;padding:8px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;box-sizing:border-box;';
  function label(t) { return el('div', 'font-size:11px;font-weight:700;color:#64748b;margin:8px 0 4px;', t); }
  function closePop() {
    ['gp5-pop', 'gp5-bd'].forEach(function (id) { var x = document.getElementById(id); if (x) x.remove(); });
  }
  function openPop(title) {
    closePop();
    var bd = el('div', 'position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:9998;');
    bd.id = 'gp5-bd'; bd.onclick = closePop;
    var pop = el('div', 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border-radius:14px;padding:20px;z-index:9999;box-shadow:0 8px 40px rgba(0,0,0,.28);width:300px;font-family:inherit;');
    pop.id = 'gp5-pop';
    pop.appendChild(el('div', 'font-weight:800;font-size:15px;margin-bottom:10px;color:#0f172a;', title));
    document.body.appendChild(bd); document.body.appendChild(pop);
    return pop;
  }
  function buttons(pop, okText, onOk) {
    var row = el('div', 'display:flex;gap:8px;margin-top:14px;');
    var c = el('button', 'flex:1;padding:9px;border:1px solid #e2e8f0;border-radius:8px;background:#f8fafc;cursor:pointer;font-weight:600;', 'Cancel');
    c.onclick = closePop;
    var ok = el('button', 'flex:2;padding:9px;border:none;border-radius:8px;background:#2563eb;color:#fff;cursor:pointer;font-weight:700;', okText);
    ok.onclick = onOk;
    row.appendChild(c); row.appendChild(ok); pop.appendChild(row);
  }

  function popupMark(nx, ny, pre) {
    var qs = qlist();
    if (!qs.length) { note('No questions loaded', 'err'); return; }
    var pop = openPop('Mark answer');
    pop.appendChild(label('QUESTION'));
    var sel = el('select', INP), first = null;
    qs.forEach(function (q) {
      var o = el('option', null, 'Q' + q.n + '  (max ' + fmt(q.max) + ')');
      o.value = q.n; sel.appendChild(o);
      if (first === null && !marks[q.n]) first = q.n;
    });
    sel.value = pre || first || qs[0].n;
    pop.appendChild(sel);
    pop.appendChild(label('SCORE'));
    var inp = el('input', INP + 'font-size:20px;font-weight:800;text-align:center;');
    inp.type = 'number'; inp.min = '0'; inp.step = '0.5';
    pop.appendChild(inp);
    pop.appendChild(label('COMMENT FOR THIS ANSWER (optional)'));
    var cm = el('textarea', INP + 'resize:none;'); cm.rows = 2;
    pop.appendChild(cm);
    var err = el('div', 'color:#dc2626;font-size:12px;min-height:16px;margin-top:4px;');
    pop.appendChild(err);
    function maxOf() { var q = qs.filter(function (x) { return x.n === sel.value; })[0]; return q ? q.max : 0; }
    function fill() {
      var m = marks[sel.value];
      inp.value = m ? m.score : '';
      cm.value = m ? (m.cmt || '') : '';
      inp.placeholder = '0 - ' + fmt(maxOf());
      err.textContent = '';
    }
    sel.onchange = fill; fill();
    buttons(pop, 'Place on paper', function () {
      var v = parseFloat(inp.value), mx = maxOf();
      if (isNaN(v) || v < 0) { err.textContent = 'Enter a score'; return; }
      if (mx > 0 && v > mx) { err.textContent = 'Maximum for this question is ' + fmt(mx); return; }
      var old = marks[sel.value];
      if (old && old.page !== page()) { err.textContent = 'Already marked on page ' + old.page + '. Go there to edit it.'; return; }
      closePop();
      var px = nx, py = ny;
      if (old && pre && String(pre) === String(sel.value) && old.page === page()) { px = old.rx + old.rw / 2; py = old.ry + old.rh / 2; }
      placeMark(sel.value, v, mx, px, py, cm.value);
    });
    setTimeout(function () { inp.focus(); }, 50);
  }

  function popupComment(nx, ny) {
    var pop = openPop('Comment on this answer');
    var ta = el('textarea', INP + 'resize:none;'); ta.rows = 3; ta.placeholder = 'Write feedback...';
    pop.appendChild(ta);
    pop.appendChild(label('COLOR'));
    var colors = ['#fde68a', '#bbf7d0', '#fecaca', '#bfdbfe'], chosen = colors[0], row = el('div', 'display:flex;gap:8px;');
    colors.forEach(function (c, i) {
      var d = el('div', 'width:26px;height:26px;border-radius:50%;cursor:pointer;box-sizing:border-box;background:' + c + ';border:3px solid ' + (i === 0 ? '#0f172a' : 'transparent') + ';');
      d.onclick = function () {
        chosen = c;
        Array.prototype.forEach.call(row.children, function (x) { x.style.borderColor = 'transparent'; });
        d.style.borderColor = '#0f172a';
      };
      row.appendChild(d);
    });
    pop.appendChild(row);
    buttons(pop, 'Place comment', function () {
      var t = ta.value.trim();
      if (!t) { ta.focus(); return; }
      closePop();
      var ac = cvs(), ctx = ac.getContext('2d');
      drawComment(ctx, t, nx * ac.width, ny * ac.height, chosen, ac.width / 700);
      persist(); note('Comment placed on paper', 'ok');
    });
    setTimeout(function () { ta.focus(); }, 50);
  }

  function hitMark(nx, ny) {
    var p = page(), k, m;
    for (k in marks) {
      m = marks[k];
      if (m.page !== p) continue;
      if (nx >= m.rx && nx <= m.rx + m.rw && ny >= m.ry && ny <= m.ry + m.rh) return k;
      if (m.crw && nx >= m.crx && nx <= m.crx + m.crw && ny >= m.cry && ny <= m.cry + m.crh) return k;
    }
    return null;
  }

  function onClick(e) {
    if (page() === 1) return;
    if (STAMP.indexOf(activeTool) < 0) return;
    var ac = cvs(), r = ac.getBoundingClientRect();
    var nx = (e.clientX - r.left) / r.width, ny = (e.clientY - r.top) / r.height;
    var ctx = ac.getContext('2d'), u = ac.width / 700;
    if (activeTool === 'mark-stamp') popupMark(nx, ny, hitMark(nx, ny));
    else if (activeTool === 'comment-stamp') popupComment(nx, ny);
    else if (activeTool === 'tick-stamp') { drawTick(ctx, nx * ac.width, ny * ac.height, u); persist(); }
    else if (activeTool === 'cross-stamp') { drawCross(ctx, nx * ac.width, ny * ac.height, u); persist(); }
  }

  function overCanvas(e) {
    var ac = cvs();
    if (!ac) return null;
    var r = ac.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) return null;
    return { nx: (e.clientX - r.left) / r.width, ny: (e.clientY - r.top) / r.height };
  }

  function init() {
    var ac = cvs();
    if (!ac) { setTimeout(init, 400); return; }
    ['mousedown', 'touchstart'].forEach(function (ev) {
      ac.addEventListener(ev, function (e) {
        if (page() === 1 || STAMP.indexOf(activeTool) >= 0) {
          e.stopImmediatePropagation();
          e.preventDefault();
        }
      }, true);
    });
    ac.addEventListener('click', onClick);
  }

  document.addEventListener('click', function (e) {
    if (page() === 1 || activeTool) return;
    if (e.target.closest && e.target.closest('#gp5-pop, #gp5-bd')) return;
    var pt = overCanvas(e);
    if (!pt) return;
    var k = hitMark(pt.nx, pt.ny);
    if (k) popupMark(pt.nx, pt.ny, k);
  });
  document.addEventListener('mousemove', function (e) {
    var cc = document.getElementById('canvasContainer');
    if (!cc || page() === 1 || activeTool) return;
    var pt = overCanvas(e);
    cc.style.cursor = (pt && hitMark(pt.nx, pt.ny)) ? 'pointer' : '';
  });

  function packAll() {
    return new Promise(function (resolve) {
      var jobs = [];
      qlist().forEach(function (q) {
        var m = marks[q.n];
        if (!m || m.cmt) return;
        var b = findBlock(q.n), t = b && b.querySelector('.fbta'), txt = t ? t.value.trim() : '';
        if (txt) jobs.push(function (cb) { repaintMark(q.n, m.score, txt, cb); });
      });
      var k = 0;
      (function next() {
        if (k < jobs.length) { jobs[k++](function () { next(); }); return; }
        var pgs = (typeof annotations !== 'undefined')
          ? Object.keys(annotations).filter(function (p) { return annotations[p]; }) : [];
        var j = 0;
        (function savePage() {
          if (j >= pgs.length) { save(); resolve(); return; }
          var pg = parseInt(pgs[j++], 10), pr;
          try { pr = _autoSavePageToServer(pg); } catch (e) { pr = null; }
          Promise.resolve(pr).then(savePage, savePage);
        })();
      })();
    });
  }

  function hookConfirm() {
    var btn = document.getElementById('btnFinish');
    if (!btn) { setTimeout(hookConfirm, 500); return; }
    btn.addEventListener('click', function (e) {
      var miss = [];
      qlist().forEach(function (q, i) {
        var v = numOrNull(questions[i] && questions[i].awarded);
        if (v !== null && !marks[q.n]) miss.push('Q' + q.n);
      });
      if (miss.length && !confirm(miss.join(', ') + ' scored in the side panel but not placed on the paper.\nThe student will not see those marks on their paper.\n\nFinish anyway?')) {
        e.stopImmediatePropagation(); e.preventDefault();
      }
    }, true);
  }

  function hookPack() {
    var btn = document.getElementById('btnFinish');
    if (!btn) { setTimeout(hookPack, 500); return; }
    btn.addEventListener('click', function (e) {
      e.stopImmediatePropagation(); e.preventDefault();
      if (finishing) return;
      finishing = true;
      var lbl = btn.textContent;
      btn.textContent = 'Saving marks to paper...';
      packAll().then(function () {
        btn.textContent = lbl; finishing = false;
        return Promise.resolve(typeof finishMarking === 'function' ? finishMarking() : null);
      }).then(function () {
        if (typeof isFinished !== 'undefined' && isFinished) { marks = {}; save(); }
      }, function (err) { finishing = false; btn.textContent = lbl; console.warn('[stamps] pack failed', err); });
    }, true);
  }

  init();
  hookConfirm();
  hookPack();
  setInterval(poll, 400);
})();