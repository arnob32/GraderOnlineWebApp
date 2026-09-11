content = """// STAMP SYSTEM - marks, comments, ticks, crosses on paper
let stampData = {}, stampLayer = null;

function initStampLayer() {
  var cc = document.getElementById("canvasContainer");
  if (!cc) return;
  stampLayer = document.getElementById("stamp-layer");
  if (!stampLayer) {
    stampLayer = document.createElement("div");
    stampLayer.id = "stamp-layer";
    stampLayer.style.cssText = "position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:25;overflow:hidden;";
    cc.appendChild(stampLayer);
  }
}

function saveStamps() {
  try { localStorage.setItem("stamps_"+SUB_ID, JSON.stringify(stampData)); } catch(e) {}
}

function loadStamps() {
  try { var d=localStorage.getItem("stamps_"+SUB_ID); if(d) stampData=JSON.parse(d); } catch(e) { stampData={}; }
}

function renderStampsForPage(page) {
  initStampLayer();
  if (!stampLayer) return;
  stampLayer.innerHTML = "";
  var stamps = stampData[page] || [];
  var canvas = document.getElementById("pdfCanvas");
  if (!canvas) return;
  var cw = canvas.width, ch = canvas.height;
  stamps.forEach(function(s, idx) {
    var el = document.createElement("div");
    el.style.cssText = "position:absolute;left:"+(s.x*cw)+"px;top:"+(s.y*ch)+"px;pointer-events:all;cursor:pointer;z-index:30;user-select:none;transform:translate(-50%,-50%);";
    if (s.type === "mark") {
      el.innerHTML = "<div style=\\"background:"+(s.color||"#dc2626")+";color:#fff;font-family:monospace;font-size:12px;font-weight:800;padding:3px 9px;border-radius:20px;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,0.35);border:2px solid rgba(255,255,255,0.5);display:flex;align-items:center;gap:4px;\\"><span style=\\"font-size:9px;opacity:.75;\\">Q"+(s.qnum||"?")+"</span><span>"+s.score+"/"+s.max+"</span></div>";
    } else if (s.type === "comment") {
      el.innerHTML = "<div style=\\"background:"+(s.color||"#fbbf24")+";color:#1a1209;font-size:10px;font-weight:600;padding:5px 9px;border-radius:7px;max-width:150px;box-shadow:0 2px 8px rgba(0,0,0,0.2);word-break:break-word;position:relative;\\">"+s.text.replace(/&/g,"&amp;").replace(/</g,"&lt;")+"<div style=\\"position:absolute;bottom:-7px;left:10px;width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-top:8px solid "+(s.color||"#fbbf24")+";\\"></div></div>";
    } else if (s.type === "tick") {
      el.innerHTML = "<div style=\\"color:"+(s.color||"#16a34a")+";font-size:26px;font-weight:900;text-shadow:0 1px 4px rgba(0,0,0,0.25);line-height:1;\\">&#10003;</div>";
    } else if (s.type === "cross") {
      el.innerHTML = "<div style=\\"color:"+(s.color||"#dc2626")+";font-size:26px;font-weight:900;text-shadow:0 1px 4px rgba(0,0,0,0.25);line-height:1;\\">&#10007;</div>";
    }
    el.title = "Click to remove";
    el.addEventListener("click", (function(i){ return function(e) {
      e.stopPropagation();
      if (confirm("Remove this stamp?")) {
        stampData[page].splice(i, 1);
        saveStamps();
        renderStampsForPage(page);
      }
    };})(idx));
    stampLayer.appendChild(el);
  });
}

function bakeStampsToCanvas(page) {
  var annoCanvas = document.getElementById("annotationCanvas");
  if (!annoCanvas) return;
  var stamps = stampData[page] || [];
  if (!stamps.length) return;
  var ctx = annoCanvas.getContext("2d");
  var cw = annoCanvas.width, ch = annoCanvas.height;
  stamps.forEach(function(s) {
    var px = s.x*cw, py = s.y*ch;
    ctx.save();
    if (s.type === "mark") {
      var label = "Q"+(s.qnum||"?")+" "+s.score+"/"+s.max;
      ctx.font = "bold 13px monospace";
      var tw = ctx.measureText(label).width;
      var bw = tw+22, bh = 24, bx = px-bw/2, by = py-bh/2, br = 12;
      ctx.beginPath();
      ctx.moveTo(bx+br,by); ctx.lineTo(bx+bw-br,by);
      ctx.quadraticCurveTo(bx+bw,by,bx+bw,by+br);
      ctx.lineTo(bx+bw,by+bh-br);
      ctx.quadraticCurveTo(bx+bw,by+bh,bx+bw-br,by+bh);
      ctx.lineTo(bx+br,by+bh);
      ctx.quadraticCurveTo(bx,by+bh,bx,by+bh-br);
      ctx.lineTo(bx,by+br);
      ctx.quadraticCurveTo(bx,by,bx+br,by);
      ctx.closePath();
      ctx.fillStyle = s.color||"#dc2626"; ctx.fill();
      ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(label, px, py);
    } else if (s.type === "comment") {
      var words = String(s.text||"").split(" "), lines = [], cur = "";
      ctx.font = "11px sans-serif";
      words.forEach(function(w){ var t=cur?cur+" "+w:w; if(ctx.measureText(t).width>150&&cur){lines.push(cur);cur=w;}else cur=t; });
      if(cur) lines.push(cur);
      var lh=15,pad=8,bw=170,bh=lines.length*lh+pad*2,bx=px-bw/2,by=py-bh/2;
      ctx.beginPath(); ctx.rect(bx,by,bw,bh);
      ctx.fillStyle = s.color||"#fbbf24"; ctx.fill();
      ctx.beginPath(); ctx.moveTo(bx+12,by+bh); ctx.lineTo(bx+6,by+bh+8); ctx.lineTo(bx+20,by+bh); ctx.closePath();
      ctx.fillStyle = s.color||"#fbbf24"; ctx.fill();
      ctx.fillStyle="#1a1209"; ctx.font="11px sans-serif"; ctx.textAlign="left"; ctx.textBaseline="top";
      lines.forEach(function(line,i){ ctx.fillText(line,bx+pad,by+pad+i*lh); });
    } else if (s.type === "tick") {
      ctx.font="bold 30px sans-serif"; ctx.fillStyle=s.color||"#16a34a";
      ctx.textAlign="center"; ctx.textBaseline="middle"; ctx.fillText("\\u2713",px,py);
    } else if (s.type === "cross") {
      ctx.font="bold 30px sans-serif"; ctx.fillStyle=s.color||"#dc2626";
      ctx.textAlign="center"; ctx.textBaseline="middle"; ctx.fillText("\\u2717",px,py);
    }
    ctx.restore();
  });
}

function doAddStamp(page, stamp) {
  if (!stampData[page]) stampData[page] = [];
  stampData[page].push(stamp);
  saveStamps();
  renderStampsForPage(page);
  setTimeout(function(){
    bakeStampsToCanvas(page);
    if (typeof _scheduleAutoSave === "function") _scheduleAutoSave(page);
    else if (typeof _autoSavePageToServer === "function") _autoSavePageToServer(page);
  }, 300);
}

function updateQScore(qnum, score) {
  document.querySelectorAll(".qblock").forEach(function(block){
    var numEl = block.querySelector(".qnum");
    if (numEl && numEl.textContent.trim() === String(qnum)) {
      var inp = block.querySelector(".pts-inp");
      if (inp) { inp.value = score; inp.dispatchEvent(new Event("input",{bubbles:true})); inp.dispatchEvent(new Event("change",{bubbles:true})); }
    }
  });
  setTimeout(function(){ if(typeof updateTotals==="function") updateTotals(); },100);
}

function removeStampPopup() {
  var p=document.getElementById("stamp-popup"); if(p) p.remove();
  var b=document.getElementById("stamp-backdrop"); if(b) b.remove();
}

function showMarkPopup(nx, ny, page) {
  removeStampPopup();
  var bd=document.createElement("div"); bd.id="stamp-backdrop";
  bd.style.cssText="position:fixed;inset:0;background:rgba(0,0,0,0.35);z-index:9998;";
  bd.addEventListener("click", removeStampPopup);
  var pop=document.createElement("div"); pop.id="stamp-popup";
  pop.style.cssText="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border-radius:14px;padding:22px;z-index:9999;box-shadow:0 8px 40px rgba(0,0,0,0.28);min-width:280px;border:1px solid #e2e8f0;font-family:inherit;";
  pop.addEventListener("click", function(e){e.stopPropagation();});
  var qOpts = "<option value=''>No specific question</option>";
  if (typeof questions !== "undefined" && Array.isArray(questions)) {
    questions.forEach(function(q){
      var qn=q.question_number||q.id, mx=q.marks||q.max_marks||"?";
      qOpts += "<option value='"+qn+"|"+mx+"'>Q"+qn+" — max "+mx+" pts</option>";
    });
  }
  pop.innerHTML = "<div style='font-weight:800;font-size:15px;margin-bottom:14px;color:#0f172a;'>&#9999; Place Mark on Paper</div>"+
    "<div style='margin-bottom:10px;'><label style='font-size:11px;font-weight:700;color:#64748b;display:block;margin-bottom:4px;'>QUESTION</label>"+
    "<select id='sp-q' style='width:100%;padding:8px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;font-family:inherit;outline:none;'>"+qOpts+"</select></div>"+
    "<div style='margin-bottom:10px;'><label style='font-size:11px;font-weight:700;color:#64748b;display:block;margin-bottom:4px;'>SCORE</label>"+
    "<input id='sp-s' type='number' min='0' step='0.5' placeholder='e.g. 3' style='width:100%;padding:9px;border:1px solid #e2e8f0;border-radius:8px;font-size:18px;font-weight:800;font-family:monospace;text-align:center;outline:none;box-sizing:border-box;'></div>"+
    "<div style='margin-bottom:14px;'><label style='font-size:11px;font-weight:700;color:#64748b;display:block;margin-bottom:6px;'>COLOR</label>"+
    "<div style='display:flex;gap:8px;'>"+
    "<div class='spc' data-c='#dc2626' style='width:24px;height:24px;border-radius:50%;background:#dc2626;cursor:pointer;border:3px solid #0f172a;flex-shrink:0;'></div>"+
    "<div class='spc' data-c='#16a34a' style='width:24px;height:24px;border-radius:50%;background:#16a34a;cursor:pointer;border:3px solid transparent;flex-shrink:0;'></div>"+
    "<div class='spc' data-c='#2563eb' style='width:24px;height:24px;border-radius:50%;background:#2563eb;cursor:pointer;border:3px solid transparent;flex-shrink:0;'></div>"+
    "<div class='spc' data-c='#d97706' style='width:24px;height:24px;border-radius:50%;background:#d97706;cursor:pointer;border:3px solid transparent;flex-shrink:0;'></div>"+
    "</div></div>"+
    "<div style='display:flex;gap:8px;'>"+
    "<button onclick='removeStampPopup()' style='flex:1;padding:9px;border:1px solid #e2e8f0;border-radius:8px;background:#f8fafc;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;'>Cancel</button>"+
    "<button id='sp-ok' style='flex:1;padding:9px;border:none;border-radius:8px;background:#dc2626;color:#fff;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;'>Place Mark</button>"+
    "</div>";
  pop.querySelectorAll(".spc").forEach(function(el){
    el.addEventListener("click",function(){ pop.querySelectorAll(".spc").forEach(function(c){c.style.border="3px solid transparent";}); this.style.border="3px solid #0f172a;"; });
  });
  pop.querySelector("#sp-ok").addEventListener("click", function(){
    var sv=pop.querySelector("#sp-s").value.trim();
    if(!sv){pop.querySelector("#sp-s").focus();return;}
    var qv=pop.querySelector("#sp-q").value;
    var selCol=[...pop.querySelectorAll(".spc")].find(function(c){return c.style.border.includes("0f172a");});
    var color=selCol?selCol.dataset.c:"#dc2626";
    var qnum="",max="?";
    if(qv){var pts=qv.split("|");qnum=pts[0];max=pts[1];}
    doAddStamp(page,{type:"mark",x:nx,y:ny,score:parseFloat(sv),max:max,qnum:qnum,color:color});
    if(qnum) updateQScore(qnum,parseFloat(sv));
    removeStampPopup();
  });
  document.body.appendChild(bd);
  document.body.appendChild(pop);
  setTimeout(function(){var el=pop.querySelector("#sp-s");if(el)el.focus();},100);
}

function showCommentPopup(nx, ny, page) {
  removeStampPopup();
  var bd=document.createElement("div"); bd.id="stamp-backdrop";
  bd.style.cssText="position:fixed;inset:0;background:rgba(0,0,0,0.35);z-index:9998;";
  bd.addEventListener("click",removeStampPopup);
  var pop=document.createElement("div"); pop.id="stamp-popup";
  pop.style.cssText="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border-radius:14px;padding:22px;z-index:9999;box-shadow:0 8px 40px rgba(0,0,0,0.28);min-width:280px;border:1px solid #e2e8f0;font-family:inherit;";
  pop.addEventListener("click",function(e){e.stopPropagation();});
  pop.innerHTML="<div style='font-weight:800;font-size:15px;margin-bottom:14px;color:#0f172a;'>&#128172; Add Comment</div>"+
    "<textarea id='sp-t' rows='3' placeholder='Write comment…' style='width:100%;padding:9px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;font-family:inherit;resize:vertical;outline:none;box-sizing:border-box;margin-bottom:10px;'></textarea>"+
    "<div style='margin-bottom:14px;'><label style='font-size:11px;font-weight:700;color:#64748b;display:block;margin-bottom:6px;'>COLOR</label>"+
    "<div style='display:flex;gap:8px;'>"+
    "<div class='spc' data-c='#fbbf24' style='width:24px;height:24px;border-radius:50%;background:#fbbf24;cursor:pointer;border:3px solid #0f172a;flex-shrink:0;'></div>"+
    "<div class='spc' data-c='#86efac' style='width:24px;height:24px;border-radius:50%;background:#86efac;cursor:pointer;border:3px solid transparent;flex-shrink:0;'></div>"+
    "<div class='spc' data-c='#fca5a5' style='width:24px;height:24px;border-radius:50%;background:#fca5a5;cursor:pointer;border:3px solid transparent;flex-shrink:0;'></div>"+
    "<div class='spc' data-c='#93c5fd' style='width:24px;height:24px;border-radius:50%;background:#93c5fd;cursor:pointer;border:3px solid transparent;flex-shrink:0;'></div>"+
    "</div></div>"+
    "<div style='display:flex;gap:8px;'>"+
    "<button onclick='removeStampPopup()' style='flex:1;padding:9px;border:1px solid #e2e8f0;border-radius:8px;background:#f8fafc;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;'>Cancel</button>"+
    "<button id='sp-ok' style='flex:1;padding:9px;border:none;border-radius:8px;background:#f59e0b;color:#fff;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;'>Place Comment</button>"+
    "</div>";
  pop.querySelectorAll(".spc").forEach(function(el){
    el.addEventListener("click",function(){ pop.querySelectorAll(".spc").forEach(function(c){c.style.border="3px solid transparent";}); this.style.border="3px solid #0f172a;"; });
  });
  pop.querySelector("#sp-ok").addEventListener("click",function(){
    var text=pop.querySelector("#sp-t").value.trim();
    if(!text){pop.querySelector("#sp-t").focus();return;}
    var selCol=[...pop.querySelectorAll(".spc")].find(function(c){return c.style.border.includes("0f172a");});
    var color=selCol?selCol.dataset.c:"#fbbf24";
    doAddStamp(page,{type:"comment",x:nx,y:ny,text:text,color:color});
    removeStampPopup();
  });
  document.body.appendChild(bd);
  document.body.appendChild(pop);
  setTimeout(function(){var el=pop.querySelector("#sp-t");if(el)el.focus();},100);
}

function initStampClick() {
  var ac=document.getElementById("annotationCanvas");
  if(!ac){setTimeout(initStampClick,600);return;}
  ac.addEventListener("click",function(e){
    if(!activeTool) return;
    var tools=["mark-stamp","comment-stamp","tick-stamp","cross-stamp"];
    if(tools.indexOf(activeTool)<0) return;
    e.stopPropagation();
    var rect=ac.getBoundingClientRect();
    var nx=(e.clientX-rect.left)/ac.width, ny=(e.clientY-rect.top)/ac.height;
    var page=(typeof currentPage!=="undefined")?currentPage:1;
    if(activeTool==="mark-stamp") showMarkPopup(nx,ny,page);
    else if(activeTool==="comment-stamp") showCommentPopup(nx,ny,page);
    else if(activeTool==="tick-stamp") doAddStamp(page,{type:"tick",x:nx,y:ny,color:"#16a34a"});
    else if(activeTool==="cross-stamp") doAddStamp(page,{type:"cross",x:nx,y:ny,color:"#dc2626"});
  });
}

function hookPageRender() {
  if(typeof renderPage==="function"){
    var orig=renderPage;
    window.renderPage=function(page){
      var r=orig.apply(this,arguments);
      if(r&&typeof r.then==="function") r.then(function(){setTimeout(function(){renderStampsForPage(page);},400);});
      else setTimeout(function(){renderStampsForPage(page);},400);
      return r;
    };
  } else { setTimeout(hookPageRender,400); }
}

function hookFinishBtn() {
  var btn=document.getElementById("btnFinish");
  if(!btn){setTimeout(hookFinishBtn,600);return;}
  btn.addEventListener("click",function(e){
    var hasStamps=Object.keys(stampData).some(function(p){return (stampData[p]||[]).length>0;});
    if(!hasStamps) return;
    bakeStampsToCanvas((typeof currentPage!=="undefined")?currentPage:1);
    if(typeof _scheduleAutoSave==="function") _scheduleAutoSave((typeof currentPage!=="undefined")?currentPage:1);
  },true);
}

document.addEventListener("DOMContentLoaded",function(){
  loadStamps();
  initStampLayer();
  initStampClick();
  hookPageRender();
  hookFinishBtn();
  setTimeout(function(){renderStampsForPage(1);},2000);
});
"""
open('app/static/JS/stamp_addon.js', 'w', encoding='utf-8').write(content)
print('Done - size:', len(content))
