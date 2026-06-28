/* grading_dashboard.js */

let questions    = [];
let pdfDoc       = null;
let curPage      = 1;
let totalPages   = 1;
let curView      = 'full';
let activeTool   = null;
let drawColor    = '#ffe94d';
let drawSize     = 4;
let isDrawing    = false;
let isFinished   = false;
let activeQIndex = 0;
let zoomLevel    = 1.0;
let renderTask   = null;
let annotations  = {};
let canvasNativeW = 0, canvasNativeH = 0;

const ZOOM_STEP  = 0.15;
const ZOOM_MIN   = 0.4;
const ZOOM_MAX   = 3.0;
const BASE_SCALE = 1.5;

let boxZoom = 1.0, boxPanX = 0, boxPanY = 0;
const BOX_ZOOM_STEP = 0.25;
const BOX_ZOOM_MIN  = 0.5;
const BOX_ZOOM_MAX  = 4.0;

// ── Box-map cache ──────────────────────────────────────────────────
let _boxCache = {};   // { pageNum: [ ...boxes ] }  — cleared on page render
let _qPageMap = null; // { qIndex: { page, localIdx } } — built once after load

const pdfCanvas  = document.getElementById('pdfCanvas');
const annoCanvas = document.getElementById('annotationCanvas');
const pdfCtx     = pdfCanvas  ? pdfCanvas.getContext('2d')  : null;
const annoCtx    = annoCanvas ? annoCanvas.getContext('2d') : null;

let floatLayer = null, floatCanvas = null, floatCtx = null, floatRegion = null;

function clearFloatLayer() {
  if (floatCanvas && floatRegion && annoCtx) {
    const r = floatRegion;

    annoCtx.drawImage(
      floatCanvas,
      0, 0, r.w, r.h,
      r.x, r.y, r.w, r.h
    );

    saveAnnotationSnap();
  }

  document
    .querySelectorAll('.focus-spotlight, .answer-float-layer')
    .forEach(el => el.remove());

  floatLayer = null;
  floatCanvas = null;
  floatCtx = null;
  floatRegion = null;
}
if (annoCanvas) {
  annoCanvas.style.pointerEvents = 'none';
  annoCanvas.style.cursor = 'default';
}

// ── Boot ───────────────────────────────────────────────────────────
window.addEventListener('load', async () => {
  const av = document.getElementById('studentAv');
  if (av) av.textContent = (STUDENT_NAME||'??').split(' ').map(w=>w[0]||'').join('').slice(0,2).toUpperCase()||'??';

  try {
    const stored = localStorage.getItem('anno_' + SUB_ID);
    if (stored) annotations = JSON.parse(stored);
  } catch(e) {}

  await loadPDF();
  await loadQuestions();
  await loadExistingMarks();
  await renderQuestions();
  checkFinishReady();
  loadExamProgress();
  buildQPageMap();              // ← build map in background, doesn't block UI
});

// ── PDF ────────────────────────────────────────────────────────────
async function loadPDF() {
  try {
    pdfDoc = await pdfjsLib.getDocument(PDF_URL).promise;
    totalPages = pdfDoc.numPages;
    await renderPage(1);
  } catch(e) {
    document.getElementById('pgInd').textContent = 'PDF Error';
    console.error('PDF load:', e);
  }
}

async function renderPage(num, keepView) {
  delete _boxCache[num];       // ← bust stale box cache for this page
  if (!pdfDoc) return;
  if (renderTask) { try { renderTask.cancel(); } catch(e) {} }
  clearFloatLayer();
  curPage = Math.max(1, Math.min(totalPages, num));
  document.getElementById('pgInd').textContent = curPage + ' / ' + totalPages;
  document.getElementById('btnPrev').disabled = curPage <= 1;
  document.getElementById('btnNext').disabled = curPage >= totalPages;
  const page     = await pdfDoc.getPage(curPage);
  const viewport = page.getViewport({ scale: BASE_SCALE * zoomLevel });
  const W = viewport.width, H = viewport.height;
  pdfCanvas.width  = annoCanvas.width  = W;
  pdfCanvas.height = annoCanvas.height = H;
  canvasNativeW = W; canvasNativeH = H;
  renderTask = page.render({ canvasContext: pdfCtx, viewport });
  await renderTask.promise;
  redrawAnnotations();
  updateMargins();
  if (curView === 'box' && !keepView) {
    if (curPage === 1) clearFloatLayer();
    else setTimeout(() => drawAnswerBox(false), 150);
  }
}

function prevPg() {
  const t = curPage - 1;
  if (t >= 1) {
    if (curView === 'box' && t === 1 && totalPages > 1) return;
    renderPage(t);
  }
}
function nextPg() { if (curPage < totalPages) renderPage(curPage + 1); }

// ── Zoom ───────────────────────────────────────────────────────────
function zoomIn() {
  if (curView === 'box' && floatLayer) { boxZoom = Math.min(BOX_ZOOM_MAX, +(boxZoom+BOX_ZOOM_STEP).toFixed(2)); applyBoxZoom(); }
  else { zoomLevel = Math.min(ZOOM_MAX, +(zoomLevel+ZOOM_STEP).toFixed(2)); applyZoom(); }
}
function zoomOut() {
  if (curView === 'box' && floatLayer) { boxZoom = Math.max(BOX_ZOOM_MIN, +(boxZoom-BOX_ZOOM_STEP).toFixed(2)); applyBoxZoom(); }
  else { zoomLevel = Math.max(ZOOM_MIN, +(zoomLevel-ZOOM_STEP).toFixed(2)); applyZoom(); }
}
function zoomReset() {
  if (curView === 'box' && floatLayer) { boxZoom=1.0; boxPanX=0; boxPanY=0; applyBoxZoom(); }
  else { zoomLevel=1.0; applyZoom(); }
}
function applyZoom() {
  document.getElementById('zoomPct').textContent = Math.round(zoomLevel*100) + '%';
  renderPage(curPage, true);
}
function applyBoxZoom() {
  document.getElementById('zoomPct').textContent = Math.round(boxZoom*100) + '%';
  if (!floatLayer || !floatCanvas || !floatRegion) return;
  floatLayer.querySelectorAll('canvas').forEach(c => {
    c.style.transformOrigin = 'top left';
    c.style.transform = 'scale(' + boxZoom + ')';
  });
  floatLayer.style.overflow = boxZoom > 1 ? 'auto' : 'hidden';
  const cr = pdfCanvas.getBoundingClientRect();
  floatLayer.style.width  = (floatRegion.w * (cr.width/pdfCanvas.width)   * boxZoom) + 'px';
  floatLayer.style.height = (floatRegion.h * (cr.height/pdfCanvas.height) * boxZoom) + 'px';
}

try {
  document.getElementById('pdfWrap').addEventListener('wheel', function(e) {
    if (e.ctrlKey || e.metaKey) { e.preventDefault(); e.deltaY < 0 ? zoomIn() : zoomOut(); }
  }, { passive: false });
} catch(e) {}

(function() {
  const wrap = document.getElementById('pdfWrap');
  if (!wrap) return;
  let lastDist = null;
  wrap.addEventListener('touchstart', e => {
    if (e.touches.length === 2) { e.preventDefault(); lastDist = Math.hypot(e.touches[0].clientX-e.touches[1].clientX, e.touches[0].clientY-e.touches[1].clientY); }
  }, { passive: false });
  wrap.addEventListener('touchmove', e => {
    if (e.touches.length === 2 && lastDist) {
      e.preventDefault();
      const d = Math.hypot(e.touches[0].clientX-e.touches[1].clientX, e.touches[0].clientY-e.touches[1].clientY);
      if (Math.abs(d - lastDist) > 6) { d > lastDist ? zoomIn() : zoomOut(); lastDist = d; }
    }
  }, { passive: false });
  wrap.addEventListener('touchend', () => { lastDist = null; });
})();

// ── View toggle ────────────────────────────────────────────────────
function setView(mode) {
  curView = mode;
  document.getElementById('btnFull').className = 'vb' + (mode === 'full' ? ' on' : '');
  document.getElementById('btnBox').className  = 'vb' + (mode === 'box'  ? ' on' : '');
  clearFloatLayer();
  const zoomLbl = document.getElementById('zoomLbl');
  const boxNav  = document.getElementById('boxNavGroup');
  if (mode === 'box') {
    if (zoomLbl) zoomLbl.textContent = 'Box zoom';
    if (boxNav)  boxNav.style.display = 'flex';
    boxZoom = 1.0;
    document.getElementById('zoomPct').textContent = '100%';
    if (curPage === 1 && totalPages > 1) {
      renderPage(2, true).then(() => { drawAnswerBox(true); updateBoxNav(); });
      toast('Skipped cover page — showing page 2', 'info');
    } else if (curPage === 1) {
      toast('Cover page — no answer boxes', 'info');
    } else {
      drawAnswerBox(true);
      updateBoxNav();
    }
  } else {
    if (zoomLbl) zoomLbl.textContent = 'Page zoom';
    if (boxNav)  boxNav.style.display = 'none';
    document.getElementById('zoomPct').textContent = Math.round(zoomLevel*100) + '%';
  }
}

function updateBoxNav() {
  const lbl = document.getElementById('boxNavLbl');
  if (lbl) lbl.textContent = 'Q' + (activeQIndex+1) + ' / ' + Math.max(1, questions.length);
}
function prevBox() {
  if (activeQIndex > 0) {
    activeQIndex--;
    boxZoom = 1.0; clearFloatLayer(); drawAnswerBox(false); updateBoxNav(); updateMargins();
    if (questions[activeQIndex]) toggleQ(questions[activeQIndex].id, true);
  }
}
function nextBox() {
  if (activeQIndex < questions.length - 1) {
    activeQIndex++;
    boxZoom = 1.0; clearFloatLayer(); drawAnswerBox(false); updateBoxNav(); updateMargins();
    if (questions[activeQIndex]) toggleQ(questions[activeQIndex].id, true);
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// ANSWER BOX DETECTION — uses PDF text layer to find exact box positions
// Each question box header contains "Q1:", "Q2:" etc. We extract text item
// positions from the PDF, find those labels, and use their Y coordinates
// plus the page geometry to compute exact box boundaries.
// ══════════════════════════════════════════════════════════════════════════════

// Extract question box rectangles from a PDF page using the text layer.
// Returns array of { x, y, width, height } in canvas pixels, sorted top→bottom.
async function _getBoxesFromTextLayer(pg, canvasW, canvasH) {
  return null;
}

// Pixel-scan fallback: find outer borders of question boxes.
// This is only used when the text layer approach fails.
function _detectBoxesFromCanvas(canvas) {
  const w = canvas.width;
  const h = canvas.height;
  const ctx = canvas.getContext('2d');

  if (!w || !h || !ctx) return [];

  const img = ctx.getImageData(0, 0, w, h).data;

  const grayAt = (x, y) => {
    x = Math.max(0, Math.min(w - 1, Math.round(x)));
    y = Math.max(0, Math.min(h - 1, Math.round(y)));
    const i = (y * w + x) * 4;
    return (img[i] + img[i + 1] + img[i + 2]) / 3;
  };

  const rgbAt = (x, y) => {
    x = Math.max(0, Math.min(w - 1, Math.round(x)));
    y = Math.max(0, Math.min(h - 1, Math.round(y)));
    const i = (y * w + x) * 4;
    return [img[i], img[i + 1], img[i + 2]];
  };

  const isBorderDark = (x, y) => grayAt(x, y) < 145;

  const isRuledLine = (x, y) => {
    const [r, g, b] = rgbAt(x, y);
    const notWhite = !(r > 245 && g > 245 && b > 245);
    const notDark = !(r < 145 && g < 145 && b < 145);

    return notWhite && notDark &&
      r >= 145 && r <= 238 &&
      g >= 145 && g <= 242 &&
      b >= 145 && b <= 248;
  };

  const mergeBands = rows => {
    const bands = [];

    for (const row of rows) {
      const last = bands[bands.length - 1];

      if (last && row.y <= last.y2 + 3) {
        last.y2 = row.y;
        last.x1 = Math.min(last.x1, row.x1);
        last.x2 = Math.max(last.x2, row.x2);
        last.score = Math.max(last.score, row.score || 0);
      } else {
        bands.push({
          y1: row.y,
          y2: row.y,
          x1: row.x1,
          x2: row.x2,
          score: row.score || 0
        });
      }
    }

    return bands.map(b => ({
      y: Math.round((b.y1 + b.y2) / 2),
      y1: b.y1,
      y2: b.y2,
      x1: b.x1,
      x2: b.x2,
      score: b.score
    }));
  };

  const horizontalRows = [];

  for (let y = Math.floor(h * 0.025); y < Math.floor(h * 0.985); y++) {
    let run = 0;
    let runStart = 0;
    let bestRun = 0;
    let bestStart = 0;
    let bestEnd = 0;

    for (let x = Math.floor(w * 0.015); x < Math.floor(w * 0.985); x++) {
      if (isBorderDark(x, y)) {
        if (run === 0) runStart = x;
        run++;

        if (run > bestRun) {
          bestRun = run;
          bestStart = runStart;
          bestEnd = x;
        }
      } else {
        run = 0;
      }
    }

    if (bestRun > w * 0.45) {
      horizontalRows.push({
        y,
        x1: bestStart,
        x2: bestEnd,
        score: bestRun
      });
    }
  }

  const hLines = mergeBands(horizontalRows)
    .filter(line => (line.x2 - line.x1) > w * 0.45)
    .sort((a, b) => a.y - b.y);

  if (hLines.length < 2) return _fallbackZones(w, h);

  const hasVerticalSide = (xGuess, y1, y2) => {
    let hits = 0;
    let samples = 0;

    const xFrom = Math.max(0, Math.floor(xGuess - 10));
    const xTo = Math.min(w - 1, Math.floor(xGuess + 10));

    const startY = Math.floor(y1 + 10);
    const endY = Math.floor(y2 - 10);

    if (endY <= startY) return false;

    for (let y = startY; y <= endY; y += 4) {
      samples++;
      let found = false;

      for (let x = xFrom; x <= xTo; x++) {
        if (isBorderDark(x, y)) {
          found = true;
          break;
        }
      }

      if (found) hits++;
    }

    return samples > 0 && hits / samples > 0.28;
  };

  const countRuledLinesInside = (x1, y1, x2, y2) => {
    const rows = [];
    const step = 4;

    const insetX = Math.max(14, (x2 - x1) * 0.025);
    const ix1 = Math.floor(x1 + insetX);
    const ix2 = Math.floor(x2 - insetX);

    if (ix2 <= ix1) return 0;

    for (let y = Math.floor(y1 + 8); y <= Math.floor(y2 - 8); y++) {
      let hits = 0;
      let sampled = 0;

      for (let x = ix1; x <= ix2; x += step) {
        sampled++;
        if (isRuledLine(x, y)) hits++;
      }

      if (sampled > 0 && hits / sampled > 0.28) {
        rows.push({ y, x1: ix1, x2: ix2, score: hits });
      }
    }

    return mergeBands(rows).length;
  };

  const boxes = [];

  for (let i = 0; i < hLines.length; i++) {
    const top = hLines[i];

    for (let j = i + 1; j < hLines.length; j++) {
      const bottom = hLines[j];
      const boxH = bottom.y - top.y;

      if (boxH < Math.max(58, h * 0.042)) continue;
      if (boxH > h * 0.62) break;

      const overlap =
        Math.min(top.x2, bottom.x2) -
        Math.max(top.x1, bottom.x1);

      if (overlap < w * 0.38) continue;

      const x1 = Math.max(0, Math.min(top.x1, bottom.x1) - 3);
      const x2 = Math.min(w - 1, Math.max(top.x2, bottom.x2) + 3);
      const boxW = x2 - x1;

      if (boxW < w * 0.45) continue;

      if (!hasVerticalSide(x1, top.y, bottom.y)) continue;
      if (!hasVerticalSide(x2, top.y, bottom.y)) continue;

      const ruled = countRuledLinesInside(x1, top.y, x2, bottom.y);
      if (ruled < 1) continue;

      boxes.push({
        x: Math.round(x1),
        y: Math.max(0, Math.round(top.y - 2)),
        width: Math.round(boxW),
        height: Math.round(Math.min(h - 1, bottom.y + 2) - Math.max(0, top.y - 2)),
        source: 'visual-border',
        ruledLines: ruled
      });

      break;
    }
  }

  const deduped = [];

  for (const box of boxes.sort((a, b) => a.y - b.y)) {
    const duplicate = deduped.find(prev => {
      const yOverlap =
        Math.min(prev.y + prev.height, box.y + box.height) -
        Math.max(prev.y, box.y);

      const xOverlap =
        Math.min(prev.x + prev.width, box.x + box.width) -
        Math.max(prev.x, box.x);

      return (
        yOverlap > Math.min(prev.height, box.height) * 0.65 &&
        xOverlap > Math.min(prev.width, box.width) * 0.65
      );
    });

    if (!duplicate) {
      deduped.push(box);
    } else {
      const oldArea = duplicate.width * duplicate.height;
      const newArea = box.width * box.height;

      if (newArea > oldArea) {
        Object.assign(duplicate, box);
      }
    }
  }

  if (deduped.length) return deduped;

  return _fallbackZones(w, h);
}

function _fallbackZones(w, h) {
  const PER_PAGE=3, top=Math.floor(h*0.10), bot=Math.floor(h*0.05);
  const zh = Math.floor((h-top-bot)/PER_PAGE);
  return Array.from({length:PER_PAGE}, (_,i) => ({
    x:Math.floor(w*0.02), y:top+i*zh, width:Math.floor(w*0.96), height:Math.max(80,zh-4), source:'fallback'
  }));
}

// Detect boxes on any page — tries text layer first, pixel scan as fallback
async function _detectBoxesOnPage(pg) {
  if (_boxCache[pg]) return _boxCache[pg];

  try {
    const page = await pdfDoc.getPage(pg);
    const viewport = page.getViewport({ scale: BASE_SCALE });

    const off = document.createElement('canvas');
    off.width = Math.round(viewport.width);
    off.height = Math.round(viewport.height);

    await page.render({
      canvasContext: off.getContext('2d'),
      viewport
    }).promise;

    _boxCache[pg] = _detectBoxesFromCanvas(off);
  } catch(e) {
    console.warn('[BoxDetect] pg=' + pg + ' error:', e);
    _boxCache[pg] = [];
  }

  return _boxCache[pg];
}

// Detect boxes on the currently visible (already rendered) page
async function detectAnswerBoxes() {
  if (!pdfCanvas || !pdfCanvas.width || !pdfCanvas.height) return [];
  return _detectBoxesFromCanvas(pdfCanvas);
}

// ── Build question → { page, localIdx } map ───────────────────────
let _buildingMap = false;
async function buildQPageMap() {
  if (_buildingMap) return;
  _buildingMap = true;
  _qPageMap = {};
  if (!pdfDoc || !questions.length) { _buildingMap = false; return; }
  // Small delay so the live page render completes first
  await new Promise(r => setTimeout(r, 400));
  let qi = 0;
  for (let pg = 2; pg <= totalPages && qi < questions.length; pg++) {
    // Wait for any active live render to finish before using off-screen canvas
    if (renderTask) { try { await renderTask.promise; } catch(e) {} }
    const boxes = await _detectBoxesOnPage(pg);
    for (let bi = 0; bi < boxes.length && qi < questions.length; bi++) {
      _qPageMap[qi] = { page: pg, localIdx: bi };
      qi++;
    }
  }
  _buildingMap = false;
  console.log('[QPageMap]', JSON.stringify(_qPageMap));
}

// ── Draw the focused answer box for the active question ────────────
async function drawAnswerBox(showToast) {
  clearFloatLayer();
  boxZoom = 1.0; boxPanX = 0; boxPanY = 0;
  document.getElementById('zoomPct').textContent = '100%';

  if (!questions.length) { if (showToast) toast('No questions loaded', 'info'); return; }

  // Ensure map is ready
  if (!_qPageMap) await buildQPageMap();

  const mapping = _qPageMap[activeQIndex];

  // Navigate to the page that contains this question's answer box.
  // keepView=true so renderPage doesn't schedule a second drawAnswerBox()
  // (we continue with the freshly rendered page right here).
  if (mapping && mapping.page !== curPage) {
    await renderPage(mapping.page, true);
  }

  if (curPage === 1) {
    if (showToast) toast('Cover page — no answer boxes', 'info');
    _showCoverPageMsg();
    return;
  }

  const boxes = await detectAnswerBoxes();
  if (!boxes.length) { if (showToast) toast('No answer boxes detected', 'info'); return; }

  // Pick the exact box for this question
  let boxIdx = 0;
  if (mapping && mapping.page === curPage) {
    boxIdx = Math.min(mapping.localIdx, boxes.length - 1);
  } else {
    // Fallback: count questions mapped to this page before activeQIndex
    let localOffset = 0;
    for (let qi = 0; qi < activeQIndex; qi++) {
      if (_qPageMap[qi] && _qPageMap[qi].page === curPage) localOffset++;
    }
    boxIdx = Math.min(localOffset, boxes.length - 1);
  }

  _renderFloatBox(boxes[boxIdx], showToast, boxIdx);
}

// ── Render spotlight + float canvas at the exact box coordinates ───
function _renderFloatBox(box, showToast, boxIdx) {
  const wrap = document.getElementById('pdfWrap');
  wrap.style.position = 'relative';
  const cr = pdfCanvas.getBoundingClientRect();
  const wr = wrap.getBoundingClientRect();

  // Scale: canvas pixels → CSS pixels
  const scaleX = cr.width  / pdfCanvas.width;
  const scaleY = cr.height / pdfCanvas.height;

  const cssX = box.x      * scaleX;
  const cssY = box.y      * scaleY;
  const cssW = box.width  * scaleX;
  const cssH = box.height * scaleY;

  const offsetX = cr.left - wr.left + wrap.scrollLeft;
  const offsetY = cr.top  - wr.top  + wrap.scrollTop;
  const absL = offsetX + cssX;
  const absT = offsetY + cssY;
  const totalW = cr.width, totalH = cr.height;

  // Four dim overlay panels surrounding the focused box
  const addSpot = (l, t, sw, sh) => {
    if (sw <= 0 || sh <= 0) return;
    const d = document.createElement('div');
    d.className = 'focus-spotlight';
    d.style.cssText = 'left:'+l+'px;top:'+t+'px;width:'+sw+'px;height:'+sh+'px';
    wrap.appendChild(d);
  };
  addSpot(offsetX,              offsetY,                         totalW, cssY);
  addSpot(offsetX,              offsetY + cssY + cssH,           totalW, Math.max(0, totalH - cssY - cssH));
  addSpot(offsetX,              offsetY + cssY,                  cssX,   cssH);
  addSpot(offsetX + cssX + cssW, offsetY + cssY, Math.max(0, totalW - cssX - cssW), cssH);

  // Float layer — sized to match the exact box in CSS pixels
  const layer = document.createElement('div');
  layer.className = 'answer-float-layer';
  layer.style.cssText = 'position:absolute;left:'+absL+'px;top:'+absT+'px;width:'+cssW+'px;height:'+cssH+'px;overflow:hidden';

  const cw = box.width, ch = box.height;  // native canvas pixels

  // PDF crop
  const pdfCrop = document.createElement('canvas');
  pdfCrop.width = cw; pdfCrop.height = ch;
  pdfCrop.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%';
  pdfCrop.getContext('2d').drawImage(pdfCanvas, box.x, box.y, cw, ch, 0, 0, cw, ch);
  layer.appendChild(pdfCrop);

  // Annotation crop
  const annoCrop = document.createElement('canvas');
  annoCrop.width = cw; annoCrop.height = ch;
  annoCrop.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none';
  annoCrop.getContext('2d').drawImage(annoCanvas, box.x, box.y, cw, ch, 0, 0, cw, ch);
  layer.appendChild(annoCrop);

  // Drawing canvas
  const drawCvs = document.createElement('canvas');
  drawCvs.width = cw; drawCvs.height = ch;
  drawCvs.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;cursor:crosshair';
  layer.appendChild(drawCvs);
  wrap.appendChild(layer);

  floatLayer  = layer;
  floatCanvas = drawCvs;
  floatCtx    = drawCvs.getContext('2d');
  floatRegion = { x: box.x, y: box.y, w: cw, h: ch };

  attachFloatListeners(drawCvs);
  if (activeTool) drawCvs.style.pointerEvents = 'auto';

  updateBoxNav();
  if (showToast) {
    const qNum = questions[activeQIndex] ? 'Q' + questions[activeQIndex].number : 'Box ' + (boxIdx + 1);
    toast('Focused on ' + qNum + ' answer box', 'info');
  }
  wrap.scrollTo({ top: Math.max(0, absT + cssH / 2 - wrap.clientHeight / 2), behavior: 'smooth' });
}

function _showCoverPageMsg() {
  const wrap = document.getElementById('pdfWrap');
  const msg  = document.createElement('div');
  msg.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,.72);color:#fff;padding:16px 24px;border-radius:12px;font-size:13px;font-weight:600;z-index:30;pointer-events:none;text-align:center';
  msg.innerHTML = '&#128196; Cover Page<br><span style="font-size:11px;opacity:.8">Navigate to page 2+ for answer boxes</span>';
  wrap.style.position = 'relative';
  wrap.appendChild(msg);
  setTimeout(() => msg.remove(), 2500);
}

// ── Annotation tools ───────────────────────────────────────────────
function selectTool(tool) {
  if (activeTool === tool) {
    activeTool = null;
    document.querySelectorAll('.atool').forEach(el => el.classList.remove('on'));
    setPointerEvents(null);
    return;
  }
  activeTool = tool;
  document.querySelectorAll('.atool').forEach(el => el.classList.remove('on'));
  const el = document.getElementById('tool-' + tool);
  if (el) el.classList.add('on');
  setPointerEvents(tool);
  toast(tool.charAt(0).toUpperCase() + tool.slice(1) + ' active', 'info');
}

function setPointerEvents(tool) {
  const active = !!tool;
  if (floatCanvas) {
    floatCanvas.style.pointerEvents = active ? 'auto' : 'none';
    if (annoCanvas) { annoCanvas.style.pointerEvents = 'none'; annoCanvas.style.cursor = 'default'; }
  } else if (annoCanvas) {
    annoCanvas.style.pointerEvents = active ? 'auto' : 'none';
    annoCanvas.style.cursor = active ? 'crosshair' : 'default';
  }
}

function setColor(el) {
  document.querySelectorAll('.cpick').forEach(e => e.classList.remove('sel'));
  el.classList.add('sel');
  drawColor = el.dataset.c;
}

try { document.getElementById('penSize').onchange = e => { drawSize = parseInt(e.target.value); }; } catch(e) {}

function getPos(e, cvs) {
  const c = cvs || annoCanvas;
  const r = c.getBoundingClientRect();
  return { x: (e.clientX-r.left)*c.width/r.width, y: (e.clientY-r.top)*c.height/r.height };
}

function applyStroke(ctx, x2, y2) {
  if (!activeTool) return;
  if (activeTool === 'pen') {
    ctx.strokeStyle = drawColor; ctx.lineWidth = drawSize;
    ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.globalAlpha = 1.0;
  } else {
    ctx.strokeStyle = drawColor; ctx.lineWidth = drawSize * 8;
    ctx.lineCap = 'round'; ctx.globalAlpha = 0.38;
  }
  ctx.lineTo(x2, y2); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(x2, y2);
}

try {
  annoCanvas.addEventListener('mousedown', e => {
    if (!activeTool) return;
    isDrawing = true;
    const {x,y} = getPos(e);
    annoCtx.beginPath(); annoCtx.moveTo(x, y);
  });
  annoCanvas.addEventListener('mousemove', e => {
    if (!isDrawing) return;
    const {x,y} = getPos(e);
    applyStroke(annoCtx, x, y);
  });
  annoCanvas.addEventListener('mouseup',    () => endDraw(annoCtx));
  annoCanvas.addEventListener('mouseleave', () => endDraw(annoCtx));
  annoCanvas.addEventListener('touchstart', e => {
    e.preventDefault(); if (!activeTool) return;
    isDrawing = true;
    const {x,y} = getPos(e.touches[0], annoCanvas);
    annoCtx.beginPath(); annoCtx.moveTo(x, y);
  }, { passive: false });
  annoCanvas.addEventListener('touchmove', e => {
    e.preventDefault(); if (!isDrawing) return;
    const {x,y} = getPos(e.touches[0], annoCanvas);
    applyStroke(annoCtx, x, y);
  }, { passive: false });
  annoCanvas.addEventListener('touchend', e => { e.preventDefault(); endDraw(annoCtx); }, { passive: false });
} catch(e) { console.warn('canvas listeners:', e); }

function attachFloatListeners(cvs) {
  const ctx = cvs.getContext('2d');
  cvs.addEventListener('mousedown', e => {
    if (!activeTool) return;
    isDrawing = true;
    const {x,y} = getPos(e, cvs);
    ctx.beginPath(); ctx.moveTo(x, y);
  });
  cvs.addEventListener('mousemove', e => {
    if (!isDrawing) return;
    const {x,y} = getPos(e, cvs);
    applyStroke(ctx, x, y);
  });
  cvs.addEventListener('mouseup',    () => endDrawFloat(ctx));
  cvs.addEventListener('mouseleave', () => endDrawFloat(ctx));
}

function endDraw(ctx) {
  if (!isDrawing) return;
  isDrawing = false; ctx.globalAlpha = 1.0;
  saveAnnotationSnap();
}
function endDrawFloat(ctx) {
  if (!isDrawing) return;

  isDrawing = false;
  ctx.globalAlpha = 1.0;

  if (!floatCanvas || !floatRegion || !annoCtx) return;

  const r = floatRegion;

  annoCtx.drawImage(
    floatCanvas,
    0, 0, r.w, r.h,
    r.x, r.y, r.w, r.h
  );

  floatCanvas.getContext('2d').clearRect(
    0, 0, floatCanvas.width, floatCanvas.height
  );

  saveAnnotationSnap();
}
function saveAnnotationSnap() {
  if (!annoCanvas) return;
  if (zoomLevel === 1.0) {
    annotations[curPage] = annoCanvas.toDataURL('image/png');
  } else {
    const bW = Math.round(canvasNativeW/zoomLevel), bH = Math.round(canvasNativeH/zoomLevel);
    const tmp = document.createElement('canvas');
    tmp.width = bW; tmp.height = bH;
    tmp.getContext('2d').drawImage(annoCanvas, 0,0,canvasNativeW,canvasNativeH, 0,0,bW,bH);
    annotations[curPage] = tmp.toDataURL('image/png');
  }
  try { localStorage.setItem('anno_' + SUB_ID, JSON.stringify(annotations)); } catch(e) {}
  // Auto-save to server in background (debounced, non-blocking)
  _scheduleAutoSave(curPage);
}

// Debounce server auto-saves so a long stroke session doesn't fire a POST
// after every mouseup. finishMarking() still force-saves every page.
let _autoSaveTimers = {};
function _scheduleAutoSave(pageNum) {
  clearTimeout(_autoSaveTimers[pageNum]);
  _autoSaveTimers[pageNum] = setTimeout(() => _autoSavePageToServer(pageNum), 1000);
}

async function _autoSavePageToServer(pageNum) {
  try {
    const dataUrl = annotations[pageNum];
    if (!dataUrl) return;
    const blob = await new Promise(res => {
      const img = new Image();
      img.onload = () => {
        const c = document.createElement('canvas');
        c.width = img.width; c.height = img.height;
        c.getContext('2d').drawImage(img, 0, 0);
        c.toBlob(res, 'image/png');
      };
      img.src = dataUrl;
    });
    if (!blob) return;
    const fd = new FormData();
    fd.append('page', String(pageNum));
    fd.append('image', blob, 'page_' + pageNum + '.png');
    const r = await fetch('/marking/' + SUB_ID + '/save-annotation-page', {
      method: 'POST', body: fd
    });
    const d = await r.json().catch(() => null);
    if (!r.ok || !d || !d.success) {
      console.warn('[Anno] Auto-save rejected for page ' + pageNum + ':', d && d.error);
      return;
    }
    console.log('[Anno] Auto-saved page ' + pageNum + ' to server');
  } catch(e) {
    console.warn('[Anno] Auto-save failed:', e);
  }
}

function redrawAnnotations() {
  if (!annoCtx || !annoCanvas) return;
  annoCtx.clearRect(0, 0, annoCanvas.width, annoCanvas.height);
  const d = annotations[curPage]; if (!d) return;
  const img = new Image();
  img.onload = () => annoCtx.drawImage(img, 0,0,img.width,img.height, 0,0,annoCanvas.width,annoCanvas.height);
  img.src = d;
}

function clearPageAnnotations() {
  clearFloatLayer();
  delete annotations[curPage];
  if (annoCtx && annoCanvas) annoCtx.clearRect(0, 0, annoCanvas.width, annoCanvas.height);
  try { localStorage.setItem('anno_' + SUB_ID, JSON.stringify(annotations)); } catch(e) {}
  // Also delete the auto-saved copy on the server — otherwise
  // embed-from-saved would re-embed the cleared annotations on Finish.
  clearTimeout(_autoSaveTimers[curPage]);
  try {
    const fd = new FormData();
    fd.append('page', String(curPage));
    fetch('/marking/' + SUB_ID + '/delete-annotation-page', { method: 'POST', body: fd });
  } catch(e) {}
  toast('Annotations cleared for page ' + curPage);
}

// ── Margin rulers ──────────────────────────────────────────────────
function updateMargins() {
  const left = document.getElementById('marginLeft');
  const right = document.getElementById('marginRight');

  if (left) {
    left.innerHTML = '';
    left.style.display = 'none';
  }

  if (right) {
    right.innerHTML = '';
    right.style.display = 'none';
  }
}

function activateQ(idx) {
  activeQIndex = idx;

  if (questions[idx]) {
    toggleQ(questions[idx].id, true);
  }

  updateBoxNav();

  if (curView === 'box') {
    boxZoom = 1.0;
    boxPanX = 0;
    boxPanY = 0;

    const zoomPct = document.getElementById('zoomPct');
    if (zoomPct) zoomPct.textContent = '100%';

    clearFloatLayer();

    setTimeout(() => {
      drawAnswerBox(false);
    }, 80);
  }
}
// ── Questions ──────────────────────────────────────────────────────
async function loadQuestions() {
  try {
    const r    = await fetch('/marking/' + SUB_ID + '/questions');
    const data = await r.json();
    questions  = (data.questions || []).map((q, idx) => ({
      id:       q.question_id || q.id,
      number:   q.question_number != null ? q.question_number : (q.number != null ? q.number : idx+1),
      text:     q.text || '',
      max:      parseFloat(q.max_marks) || 0,
      awarded:  q.awarded_marks != null ? parseFloat(q.awarded_marks) : null,
      feedback: q.comment || '',
    }));
  } catch(e) { console.error('loadQuestions:', e); questions = []; }
  _qPageMap = null;  // ← invalidate map whenever questions reload
}

async function loadExistingMarks() {
  try {
    const r = await fetch('/marking/' + SUB_ID);
    if (!r.ok) return;
    const m = await r.json();
    if (m.comments) document.getElementById('overallFb').value = m.comments;
    if (m.status === 'returned') { isFinished = true; showSentState(); }
    else if (m.status === 'marked') { isFinished = true; showFinishedState(); }
  } catch(e) {}
}

async function renderQuestions() {
  const con = document.getElementById('qContainer');
  if (!questions.length) {
    con.innerHTML = '<div style="text-align:center;padding:24px;color:var(--ink-4);font-size:13px">No questions found.</div>';
    return;
  }
  con.innerHTML = '';
  for (let i = 0; i < questions.length; i++) {
    const q = questions[i];
    let addC = '', subC = '';
    try {
      const tr = await fetch('/api/feedback-templates?question_id='+q.id+'&exam_id='+EXAM_ID+'&teacher_id='+TEACHER_ID);
      if (tr.ok) {
        const tmpls = await tr.json();
        const aT = (tmpls||[]).filter(t=>t.points>=0);
        const sT = (tmpls||[]).filter(t=>t.points<0);
        if (aT.length) addC = '<div class="tmpl-lbl">Quick add</div><div class="chips">' + aT.map(t=>'<div class="chip chip-a" onclick="applyTmpl('+q.id+','+t.points+')">+'+t.points+' '+esc(t.label)+'</div>').join('') + '</div>';
        if (sT.length) subC = '<div class="tmpl-lbl">Quick deduct</div><div class="chips">' + sT.map(t=>'<div class="chip chip-s" onclick="applyTmpl('+q.id+','+t.points+')">'+t.points+' '+esc(t.label)+'</div>').join('') + '</div>';
      }
    } catch(e) {}
    const isDone = q.awarded !== null;
    const el = document.createElement('div');
    el.className = 'qblock' + (isDone?' done':'') + (i===0?' active-q':'');
    el.id = 'qb-' + q.id;
    el.innerHTML =
      '<div class="qhd" onclick="onQhdClick('+q.id+','+i+')">' +
        '<div class="qnum'+(isDone?' done':(i===0?' active':''))+'" id="qnum-'+q.id+'">Q'+q.number+'</div>' +
        '<div class="qtxt">'+esc((q.text||'').slice(0,55))+(q.text.length>55?'…':'')+'</div>' +
        '<span class="qpts" id="qpts-'+q.id+'">'+(isDone?q.awarded:'—')+'</span>' +
        '<span class="qmax">/'+q.max+'</span>' +
        '<span class="qchv'+(i===0?' open':'')+'" id="qchv-'+q.id+'">▾</span>' +
      '</div>' +
      '<div class="qbody" id="qbody-'+q.id+'" style="display:'+(i===0?'block':'none')+'">' +
        '<div class="step-grid">'+buildStepBtns(q.id,q.max)+'</div>' +
        '<div class="pts-row">' +
          '<input type="number" class="pts-inp" id="pi-'+q.id+'" min="0" max="'+q.max+'" step="0.5" value="'+(isDone?q.awarded:'')+'" placeholder="—" oninput="onPts('+q.id+')">' +
          '<span class="pts-max">/ '+q.max+' pts</span>' +
          '<button class="pq" onclick="setAw('+q.id+','+q.max+')">Full</button>' +
          '<button class="pq" onclick="setAw('+q.id+',0)">Zero</button>' +
        '</div>' +
        '<input type="range" class="pts-slider" id="sl-'+q.id+'" min="0" max="'+q.max+'" step="0.5" value="'+(isDone?q.awarded:0)+'" oninput="onSlide('+q.id+')">' +
        (addC||subC?'<div style="margin-bottom:6px">'+addC+subC+'</div>':'') +
        '<textarea class="fbta" id="fb-'+q.id+'" rows="2" placeholder="Feedback…" oninput="onFb('+q.id+')">'+esc(q.feedback)+'</textarea>' +
      '</div>';
    con.appendChild(el);
  }
  updateScore(); checkFinishReady(); updateMargins();
}

function buildStepBtns(qid, max) {
  const steps = [];
  if (max>=0.5) steps.push(0.5); if (max>=1) steps.push(1);
  if (max>=4)   steps.push(2);   if (max>=10) steps.push(5);
  return [...new Set(steps.filter(s=>s<=max))].map(s =>
    '<button class="step-btn" onclick="stepMark('+qid+','+s+')">+'+s+'</button>' +
    '<button class="step-btn" onclick="stepMark('+qid+',-'+s+')">−'+s+'</button>'
  ).join('');
}

function onQhdClick(qid, idx) {
  activeQIndex = idx;

  // Open selected question's marking + feedback fields
  toggleQ(qid, true);

  updateBoxNav();

  if (curView === 'box') {
    boxZoom = 1.0;
    boxPanX = 0;
    boxPanY = 0;

    const zoomPct = document.getElementById('zoomPct');
    if (zoomPct) zoomPct.textContent = '100%';

    clearFloatLayer();

    setTimeout(() => {
      drawAnswerBox(false);
    }, 80);
  }
}

function toggleQ(qid, forceOpen) {
  const body = document.getElementById('qbody-'+qid);
  const open = body && body.style.display === 'block';
  const newOpen = forceOpen !== undefined ? forceOpen : !open;
  questions.forEach(q => {
    const b=document.getElementById('qbody-'+q.id), c=document.getElementById('qchv-'+q.id);
    const bl=document.getElementById('qb-'+q.id), nm=document.getElementById('qnum-'+q.id);
    if(b)b.style.display='none'; if(c)c.classList.remove('open');
    if(bl)bl.classList.remove('active-q'); if(nm&&q.awarded===null)nm.classList.remove('active');
  });
  if (newOpen) {
    if(body)body.style.display='block';
    const chv=document.getElementById('qchv-'+qid); if(chv)chv.classList.add('open');
    const bl=document.getElementById('qb-'+qid), nm=document.getElementById('qnum-'+qid);
    if(bl)bl.classList.add('active-q');
    const q=questions.find(q=>q.id===qid);
    if(nm&&q&&q.awarded===null)nm.classList.add('active');
  }
}

function setAw(qid, val) {
  const q=questions.find(q=>q.id===qid); if(!q)return;
  val=Math.max(0,Math.min(q.max,parseFloat(val)||0)); q.awarded=val;
  const pi=document.getElementById('pi-'+qid), sl=document.getElementById('sl-'+qid);
  const pt=document.getElementById('qpts-'+qid), nm=document.getElementById('qnum-'+qid);
  const qb=document.getElementById('qb-'+qid);
  if(pi)pi.value=val; if(sl)sl.value=val; if(pt)pt.textContent=val;
  if(nm)nm.className='qnum done'; if(qb)qb.className='qblock done active-q';
  updateScore(); checkFinishReady(); updateMargins();
}
function onPts(qid) {
  const q=questions.find(q=>q.id===qid), pi=document.getElementById('pi-'+qid);
  if(!q||!pi)return;
  const v=parseFloat(pi.value);
  q.awarded=isNaN(v)?null:Math.max(0,Math.min(q.max,v));
  const sl=document.getElementById('sl-'+qid), pt=document.getElementById('qpts-'+qid);
  const nm=document.getElementById('qnum-'+qid), qb=document.getElementById('qb-'+qid);
  if(sl&&q.awarded!==null)sl.value=q.awarded;
  if(pt)pt.textContent=q.awarded!==null?q.awarded:'—';
  if(nm)nm.className='qnum'+(q.awarded!==null?' done':'');
  if(qb)qb.className='qblock'+(q.awarded!==null?' done':'')+' active-q';
  updateScore(); checkFinishReady(); updateMargins();
}
function onSlide(qid){const sl=document.getElementById('sl-'+qid);if(sl)setAw(qid,parseFloat(sl.value));}
function onFb(qid){const q=questions.find(q=>q.id===qid),el=document.getElementById('fb-'+qid);if(q&&el)q.feedback=el.value;}
function stepMark(qid,delta){const q=questions.find(q=>q.id===qid);if(!q)return;setAw(qid,(q.awarded!==null?q.awarded:0)+delta);}
function applyTmpl(qid,pts){const q=questions.find(q=>q.id===qid);if(!q)return;setAw(qid,(q.awarded!==null?q.awarded:0)+pts);}

function updateScore() {
  let total=0,maxT=0,graded=0;
  questions.forEach(q=>{if(q.awarded!==null){total+=q.awarded;graded++;}maxT+=q.max;});
  const pct=maxT>0?Math.round(total/maxT*100):0, ppct=questions.length>0?Math.round(graded/questions.length*100):0;
  document.getElementById('dispAw').textContent=total;
  document.getElementById('dispMax').textContent=maxT||MAX_SCORE||'—';
  document.getElementById('dispPct').textContent=maxT>0?pct+'%':'—';
  document.getElementById('progTxt').textContent=graded+' / '+questions.length+' marked';
  const fill=document.getElementById('progFill');
  fill.style.width=ppct+'%'; fill.className='prog-fill'+(ppct===100?' complete':'');
}

function checkFinishReady() {
  if (isFinished) return;
  const allMarked=questions.length>0&&questions.every(q=>q.awarded!==null);
  document.getElementById('btnFinish').disabled=!allMarked;
  const banner=document.getElementById('statusBanner');
  if(allMarked&&questions.length){banner.className='status-banner complete show';banner.textContent='✓ All '+questions.length+' questions marked — ready to finish';}
  else{const rem=questions.filter(q=>q.awarded===null).length;if(rem>0){banner.className='status-banner partial show';banner.textContent=rem+' question'+(rem!==1?'s':'')+' still need marking';}else banner.className='status-banner';}
}
function showFinishedState(){document.getElementById('btnFinish').style.display='none';document.getElementById('btnSend').style.display='flex';const b=document.getElementById('statusBanner');b.className='status-banner complete show';b.textContent='✓ Marked — use Student Directory to send to student';}
function showSentState(){document.getElementById('btnFinish').style.display='none';document.getElementById('btnSend').style.display='none';const b=document.getElementById('statusBanner');b.className='status-banner sent show';b.textContent='✓ This paper has been sent to the student';}

async function saveDraft(){if(!questions.filter(q=>q.awarded!==null).length){toast('Mark at least one question first','err');return;}const ok=await saveMarks('marked');if(ok)toast('Draft saved ✓','ok');}

async function finishMarking() {
  const unmarked=questions.filter(q=>q.awarded===null);
  if(unmarked.length){toast(unmarked.length+' question(s) still need marking','err');return;}
  if(!questions.length){toast('No questions','err');return;}
  const btn=document.getElementById('btnFinish');
  btn.disabled=true; btn.textContent='Saving…';
  try {
    const ok=await saveMarks('marked');
    if(!ok){btn.disabled=false;btn.textContent='✓ Finish Marking';return;}
    clearFloatLayer();
    // Reload annotations from localStorage — most reliable source
    try {
      const stored = localStorage.getItem('anno_' + SUB_ID);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Merge: keep any in-memory annotations not yet in localStorage
        Object.assign(annotations, parsed);
      }
    } catch(e) {}
    const annoPages = Object.keys(annotations).filter(pg => annotations[pg]);
    console.log('[Finish] Annotation pages:', annoPages);

    let embedOk = true;   // true when there's nothing to embed or embed succeeded
    if(annoPages.length){
      btn.textContent='Embedding annotations…';
      toast('Embedding ' + annoPages.length + ' annotated page(s)…','info');
      // Cancel pending debounced saves, then force-save every page to server
      for (const pg of annoPages) {
        clearTimeout(_autoSaveTimers[pg]);
        await _autoSavePageToServer(parseInt(pg));
      }
      // Then embed from saved server files — and CHECK the result.
      // A silent failure here previously meant the student received the
      // un-annotated PDF with no warning to the teacher.
      try {
        const r = await fetch('/marking/' + SUB_ID + '/embed-from-saved', {method:'POST'});
        const d = await r.json().catch(() => null);
        console.log('[Anno] Embed result:', d);
        embedOk = !!(r.ok && d && d.success);
        if (embedOk) {
          // PDF now has the annotations baked in — clear local copies so
          // reopening this paper can't double-embed old strokes.
          try { localStorage.removeItem('anno_' + SUB_ID); } catch(e) {}
          annotations = {};
        }
      } catch(e) {
        console.warn('[Anno] Embed error:', e);
        embedOk = false;
      }
    }

    isFinished=true; showFinishedState();

    if (embedOk) {
      toast('Marking complete ✓ — use Student Directory to send','ok');
      // Teacher stays on page - send from Student Directory
    } else {
      // Marks are saved, but the annotated PDF was NOT produced.
      // Don't auto-redirect — make sure the teacher sees this before sending.
      toast('Marks saved, but annotations could NOT be embedded into the PDF. ' +
            'Your drawings are kept — reload and Finish again to retry before sending.','err');
      btn.style.display='inline-flex';
      btn.disabled=false; btn.textContent='↻ Retry Finish (embed failed)';
      isFinished=false;
    }
  } catch(e) {
    toast('Error: '+e.message,'err');
    btn.disabled=false; btn.textContent='✓ Finish Marking';
  }
}

async function sendToStudent() {
  if(!isFinished){toast('Finish marking first','err');return;}
  const btn=document.getElementById('btnSend');
  btn.disabled=true; btn.textContent='Sending…';
  try {
    const r=await fetch('/marking/'+SUB_ID+'/send-to-student',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({teacher_id:TEACHER_ID})});
    if(!r.ok){const e=await r.json().catch(()=>{});throw new Error(e.detail||'Send failed');}
    toast('Sent to student ✓','ok');showSentState();
    // Redirect handled by Student Directory
  } catch(e) {
    toast('Error: '+e.message,'err');
    btn.disabled=false; btn.textContent='✈ Send to Student';
  }
}

async function loadExamProgress() {
  try {
    const r=await fetch('/marking/queue-status?exam_id='+EXAM_ID);if(!r.ok)return;
    const d=await r.json();
    const banner=document.getElementById('examProgressBanner');if(!banner)return;
    const total=d.total||0,done=d.done||0,pending=d.pending||0;
    if(total>1){
      banner.style.display='block';
      banner.innerHTML='<span style="font-weight:700">Exam progress:</span> '+done+' / '+total+' papers marked'+
        (pending>0?' &nbsp;·&nbsp; <span style="color:var(--amber)">'+pending+' remaining</span>':' &nbsp;·&nbsp; <span style="color:var(--green)">✓ All done</span>')+
        (d.next_id&&d.next_id!==SUB_ID?' &nbsp;·&nbsp; <a href="/uploads/grade-submission/'+d.next_id+'" style="color:var(--primary);font-weight:700">Grade next →</a>':'');
    }
  } catch(e) {}
}

async function saveMarks(status) {
  const feedback=document.getElementById('overallFb').value.trim();
  const total=questions.reduce((s,q)=>s+(q.awarded||0),0);
  const maxPoss=questions.reduce((s,q)=>s+q.max,0);
  const qmarks=questions.filter(q=>q.awarded!==null).map(q=>({
    question_id:q.id,
    question_number:q.number!=null?parseInt(q.number):0,
    awarded_marks:parseFloat(q.awarded)||0,
    max_marks:parseFloat(q.max)||0,
    comment:q.feedback||''
  }));
  if(!qmarks.length){toast('No marks to save','err');return false;}
  try {
    const r1=await fetch('/marking/'+SUB_ID+'/questions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question_marks:qmarks,feedback,teacher_id:TEACHER_ID,status})});
    if(!r1.ok){const e=await r1.json().catch(()=>{});throw new Error(e.detail||'HTTP '+r1.status);}
    const fd=new FormData();
    fd.append('marks',total);fd.append('max_score',maxPoss||100);
    fd.append('feedback',feedback);fd.append('status',status);fd.append('teacher_id',TEACHER_ID);
    await fetch('/marking/'+SUB_ID,{method:'POST',body:fd});
    return true;
  } catch(e) { toast('Save error: '+e.message,'err'); return false; }
}

function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function toast(msg,type){const t=document.getElementById('toast');t.textContent=msg;t.className='toast show'+(type?' '+type:'');clearTimeout(window._tt);window._tt=setTimeout(()=>t.classList.remove('show'),3000);}
// Show finished state - reveal Student Directory link
function showFinishedState() {
  const btnFinish = document.getElementById('btnFinish');
  const btnSend   = document.getElementById('btnSend');
  if (btnFinish) { btnFinish.disabled = true; btnFinish.textContent = 'Marked'; }
  if (btnSend)   { btnSend.style.display = 'inline-flex'; }
}


function showFinishedState() {
  var btnFinish = document.getElementById('btnFinish');
  var btnSend   = document.getElementById('btnSend');
  if (btnFinish) { btnFinish.disabled = true; btnFinish.textContent = 'Marked'; }
  if (btnSend)   { btnSend.style.display = 'inline-flex'; }
}

function showSentState() {
  var btnSend = document.getElementById('btnSend');
  if (btnSend) { btnSend.textContent = 'Sent'; btnSend.style.pointerEvents = 'none'; }
}
