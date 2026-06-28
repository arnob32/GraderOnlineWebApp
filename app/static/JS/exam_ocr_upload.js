// exam_ocr_upload.js — all upload logic
var _allSubjectOpts=[],_allExamOpts=[],_examId='',_examName='';
var _activeSemId='',_activeDeptId='',_students=[],_uploadedCodes={};
var _files=[],_pdfData={},_mode='files',_unmatchedPaths=[];

document.addEventListener('DOMContentLoaded',function(){
  var subSel=document.getElementById('subjectSelect');
  var examSel=document.getElementById('examSelect');

  Array.from(subSel.options).forEach(function(o){
    if(!o.value)return;
    _allSubjectOpts.push({value:o.value,text:o.textContent.trim(),
      semId:o.getAttribute('data-sem')||'',deptId:o.getAttribute('data-dept')||''});
  });

  // FIX: cache data-subject so we can filter exams by subject
  Array.from(examSel.options).forEach(function(o){
    if(!o.value)return;
    _allExamOpts.push({value:o.value,text:o.textContent.trim(),
      deptId:o.getAttribute('data-dept')||'',
      subjectId:o.getAttribute('data-subject')||''});
  });

  document.getElementById('semesterSelect').addEventListener('change',onSemesterChange);
  document.getElementById('subjectSelect').addEventListener('change',onSubjectChange);
  document.getElementById('examSelect').addEventListener('change',onExamSelect);
  document.getElementById('subjectSelect').disabled=false;
  updateUploadBtn();
  checkMLStatus();
});

function setMode(m){
  _mode=m;
  document.getElementById('modeFiles').classList.toggle('active',m==='files');
  document.getElementById('modeFolder').classList.toggle('active',m==='folder');
  clearFiles();
}

function dzClick(){
  var inp=(_mode==='folder')?document.getElementById('inputFolder'):document.getElementById('inputFiles');
  inp.value='';inp.click();
}
function dzDragOver(e){e.preventDefault();e.stopPropagation();document.getElementById('dropzone').classList.add('drag-over');}
function dzDragLeave(){document.getElementById('dropzone').classList.remove('drag-over');}
function dzDrop(e){
  e.preventDefault();e.stopPropagation();
  document.getElementById('dropzone').classList.remove('drag-over');
  var files=e.dataTransfer&&e.dataTransfer.files?Array.from(e.dataTransfer.files):[];
  handleFiles(files);
}
function handleInputChange(inp){handleFiles(inp.files);}

function handleFiles(fileList){
  // FIX: images only, no PDF
  _files=Array.from(fileList).filter(function(f){return /\.(jpe?g|png|webp|bmp|tiff)$/i.test(f.name);});
  renderFileList();updateUploadBtn();
}

function clearFiles(){_files=[];renderFileList();updateUploadBtn();}

function renderFileList(){
  var title=document.getElementById('dzTitle');
  var flist=document.getElementById('fileList');
  if(_files.length){
    title.textContent=_files.length+' file'+(_files.length!==1?'s':'')+' selected';
    flist.innerHTML=_files.slice(0,5).map(function(f){
      var sz=f.size>1048576?(f.size/1048576).toFixed(1)+' MB':Math.round(f.size/1024)+' KB';
      return '<div class="file-item"><span class="fi-ico">🖼</span><span class="fi-name">'+esc(f.name)+'</span><span class="fi-size">'+sz+'</span></div>';
    }).join('')+(_files.length>5?'<div style="padding:4px 10px;font-size:.68rem;color:var(--text4);">…and '+(_files.length-5)+' more</div>':'');
  }else{title.textContent='Drop Exam Papers Here';flist.innerHTML='';}
}

function setPills(n){
  [1,2,3].forEach(function(i){
    var el=document.getElementById('cp'+i);if(!el)return;
    el.classList.toggle('active',i<=n);el.classList.toggle('done',i<n);
  });
}

function rebuildSelect(sel,placeholder,items){
  sel.innerHTML='<option value="">'+placeholder+'</option>';
  items.forEach(function(item){
    var o=document.createElement('option');o.value=item.value;o.textContent=item.text;
    if(item.deptId!==undefined)o.setAttribute('data-dept',item.deptId);
    if(item.semId!==undefined)o.setAttribute('data-sem',item.semId);
    if(item.subjectId!==undefined)o.setAttribute('data-subject',item.subjectId);
    sel.appendChild(o);
  });
}

function onSemesterChange(){
  _activeSemId=document.getElementById('semesterSelect').value;_activeDeptId='';
  setPills(_activeSemId?2:1);
  var subSel=document.getElementById('subjectSelect');
  var list=_activeSemId
    ?_allSubjectOpts.filter(function(s){return !s.semId||s.semId===_activeSemId;})
    :_allSubjectOpts.slice();
  rebuildSelect(subSel,'— all subjects —',list);
  subSel.disabled=false;
  filterExams();
}

function onSubjectChange(){
  var subSel=document.getElementById('subjectSelect');
  var opt=subSel.options[subSel.selectedIndex];
  _activeDeptId=(opt&&opt.value)?(opt.getAttribute('data-dept')||''):'';
  resetExamSelection();filterExams();
}

function resetExamSelection(){
  _examId='';_examName='';
  var pill=document.getElementById('examPill');
  if(pill)pill.classList.remove('show');
  document.getElementById('checklistCard').classList.add('hidden');
  updateUploadBtn();
}

// FIX: filter exam dropdown by selected subject
function filterExams(){
  var subSel=document.getElementById('subjectSelect');
  var activeSubjectId=subSel?subSel.value:'';
  var filtered=activeSubjectId
    ?_allExamOpts.filter(function(e){return !e.subjectId||e.subjectId===activeSubjectId;})
    :_allExamOpts.slice();
  rebuildSelect(document.getElementById('examSelect'),'— choose an exam —',filtered);
}

function onExamSelect(){
  var sel=document.getElementById('examSelect');
  var opt=sel.options[sel.selectedIndex];
  _examId=sel.value;_examName=opt?opt.textContent.trim():'';
  var pill=document.getElementById('examPill');
  if(_examId){
    document.getElementById('examPillText').textContent=_examName;
    if(pill)pill.classList.add('show');
    setPills(3);
    document.getElementById('emptyState').classList.add('hidden');
    loadChecklist(_examId);
  }else{
    if(pill)pill.classList.remove('show');
    document.getElementById('checklistCard').classList.add('hidden');
  }
  updateUploadBtn();
}

function loadChecklist(examId){
  document.getElementById('checklistCard').classList.remove('hidden');
  document.getElementById('studentList').innerHTML='<div style="padding:8px;color:var(--text4);font-size:.76rem">Loading…</div>';
  fetch('/api/exams/'+examId+'/students')
    .then(function(r){return r.json();})
    .then(function(data){
      // Handle both list response and {students:[]} response
      _students=Array.isArray(data)?data:(data.students||[]);
      _uploadedCodes={};
      _students.forEach(function(s){
        if(s.submitted)_uploadedCodes[s.student_code]={status:s.status||'uploaded',submission_id:s.submission_id};
      });
      renderChecklist();populateQuickAssign();
    })
    .catch(function(e){
      console.error('loadChecklist error:',e);
      document.getElementById('studentList').innerHTML='<div style="padding:8px;color:var(--rose);font-size:.76rem">Could not load students.</div>';
    });
}

var STATUS_LABELS={uploaded:'Uploaded',assigned:'Assigned',marked:'Marked',returned:'Released',duplicate:'Duplicate'};

function renderChecklist(){
  var list=document.getElementById('studentList');
  var up=0,miss=0;
  if(!_students.length){
    list.innerHTML='<div style="padding:8px;color:var(--text4);font-size:.76rem">No students found.</div>';
    setCounters(0,0);return;
  }
  list.innerHTML=_students.map(function(s){
    var rec=_uploadedCodes[s.student_code];var done=!!rec;
    var isDup=rec&&rec.status==='duplicate';var isAsg=rec&&rec.status==='assigned';
    if(done)up++;else miss++;
    var cls=isDup?'duplicate':(isAsg?'assigned':(done?'uploaded':'missing'));
    var bCls=isDup?'dup':(isAsg?'assigned':(done?'up':'miss'));
    var check=isDup?'⚠':(done?'✓':'');
    var lbl=isDup?'Duplicate':(done?(STATUS_LABELS[rec.status]||rec.status):'Pending');
    return '<div class="student-row '+cls+'" id="chk-'+esc(s.student_code)+'">'
      +'<div class="sr-check">'+check+'</div>'
      +'<div class="sr-info"><div class="sr-name">'+esc(s.name)+'</div>'
      +'<div class="sr-id">'+esc(s.student_code)+'</div></div>'
      +'<span class="sr-badge '+bCls+'">'+lbl+'</span></div>';
  }).join('');
  setCounters(up,miss);
}

function setCounters(up,miss){
  var total=up+miss;
  var u=document.getElementById('cstatUp');var m=document.getElementById('cstatMiss');var b=document.getElementById('checklistBadge');
  if(u)u.textContent=up+' uploaded';if(m)m.textContent=miss+' missing';if(b)b.textContent=up+' / '+total+' Ready';
}

function markStudentStatus(code,status,submId){
  _uploadedCodes[code]={status:status,submission_id:submId};
  var row=document.getElementById('chk-'+code);if(!row)return;
  var isDup=status==='duplicate';var isAsg=status==='assigned';
  var cls=isDup?'duplicate':(isAsg?'assigned':'uploaded');
  var bCls=isDup?'dup':(isAsg?'assigned':'up');
  row.className='student-row '+cls;
  row.querySelector('.sr-check').innerHTML=isDup?'⚠':'✓';
  var badge=row.querySelector('.sr-badge');badge.className='sr-badge '+bCls;badge.textContent=status;
  var up=0,miss=0;_students.forEach(function(s){if(_uploadedCodes[s.student_code])up++;else miss++;});setCounters(up,miss);
}

function populateQuickAssign(){
  var sel=document.getElementById('quickAssignSelect');if(!sel)return;
  sel.innerHTML='<option value="">— select student —</option>';
  (_students||[]).forEach(function(s){
    var o=document.createElement('option');o.value=s.id;
    o.textContent=(s.name||'')+(s.student_code?' ('+s.student_code+')':'');sel.appendChild(o);
  });
}

function updateUploadBtn(){
  var btn=document.getElementById('uploadBtn');
  if(btn)btn.disabled=!(_examId&&_files.length>0);
}

function showToast(msg,ok){
  var t=document.getElementById('toast');if(!t)return;
  t.textContent=msg;t.className='toast show'+(ok===true?' ok':(ok===false?' err':''));
  setTimeout(function(){t.classList.remove('show');},3500);
}

function checkMLStatus(){
  fetch('/api/exams/scanner/status')
    .then(function(r){return r.json();})
    .then(function(d){
      var badge=document.getElementById('mlStatusBadge');if(!badge)return;
      if(d.model_loaded){badge.innerHTML='<span class="ml-dot"></span>ML Ready';badge.className='ml-badge';}
      else{badge.innerHTML='<span class="ml-dot"></span>No OCR Model';badge.className='ml-badge warn';}
    }).catch(function(){});
}

async function doUpload(){
  if(!_examId){showToast('Please select an exam first.',false);return;}
  if(!_files.length){showToast('Please select image files to upload.',false);return;}
  var btn=document.getElementById('uploadBtn');
  var overlay=document.getElementById('loadingOverlay');
  var loSub=document.getElementById('loSub');
  if(btn){btn.disabled=true;btn.textContent='Processing…';}
  if(overlay)overlay.classList.add('show');
  if(loSub)loSub.textContent='Uploading '+_files.length+' image(s) and running OCR…';
  var fd=new FormData();
  fd.append('exam_id',_examId);
  _files.forEach(function(f){fd.append('files',f);});
  try{
    var res=await fetch('/api/exams/upload',{method:'POST',body:fd});
    var rawText=await res.text();var data;
    try{data=JSON.parse(rawText);}catch(je){throw new Error('Server error: '+rawText.substring(0,200));}
    if(!res.ok)throw new Error(data.detail||data.message||'Upload failed');
    (data.results||[]).forEach(function(r){
      if(!r.extracted_id)return;
      if(r.status==='success')markStudentStatus(r.extracted_id,'uploaded',r.submission_id);
      if(r.status==='duplicate')markStudentStatus(r.extracted_id,'duplicate',null);
    });
    var matched=data.matched_students||0;
    var unmatched=data.unmatched_students||0;
    showToast(matched+' matched, '+unmatched+' unmatched',matched>0);
    showResults(data);
    showDupWarnings(data.results||[]);
    if(matched>0){document.getElementById('viewPapersBanner').classList.add('show');showPdfSection(data);}
    var unmatchedPages=(data.results||[]).filter(function(r){return r.status==='unmatched'||r.status==='failed';});
    if(unmatchedPages.length)renderUnmatched(unmatchedPages);
    clearFiles();
  }catch(err){
    showToast(err.message,false);
  }finally{
    if(btn){btn.disabled=false;btn.innerHTML='<svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg> Upload &amp; Process';}
    if(overlay)overlay.classList.remove('show');
  }
}

function showDupWarnings(results){
  var dups=results.filter(function(r){return r.status==='duplicate'&&r.duplicate;});
  var wrap=document.getElementById('dupBannerWrap');var list=document.getElementById('dupList');
  if(!dups.length||!wrap||!list)return;
  wrap.classList.remove('hidden');
  list.innerHTML=dups.map(function(r){
    return '<div class="dup-item"><span class="dup-code">'+esc(r.extracted_id||'')+'</span><span style="flex:1">'+esc(r.extracted_name||'')+'</span></div>';
  }).join('');
}

function showResults(data){
  var card=document.getElementById('resultsCard');if(!card)return;
  card.classList.remove('hidden');
  var dupCount=(data.results||[]).filter(function(r){return r.status==='duplicate';}).length;
  document.getElementById('statsRow').innerHTML=
    '<div class="stat-box g"><div class="stat-val">'+(data.matched_students||0)+'</div><div class="stat-lbl">Matched</div></div>'
    +'<div class="stat-box r"><div class="stat-val">'+(data.unmatched_students||0)+'</div><div class="stat-lbl">Unmatched</div></div>'
    +'<div class="stat-box a"><div class="stat-val">'+dupCount+'</div><div class="stat-lbl">Duplicates</div></div>'
    +'<div class="stat-box"><div class="stat-val">'+(data.total_pages||0)+'</div><div class="stat-lbl">Total</div></div>';
  document.getElementById('resultList').innerHTML=(data.results||[]).map(function(r){
    var cls='s-'+(r.status==='success'?'success':r.status==='duplicate'?'duplicate':r.status==='unmatched'?'unmatched':'failed');
    var badge=r.status==='success'?'<span class="ri-badge g">✓ '+esc(r.extracted_id||'')+'</span>'
      :r.status==='duplicate'?'<span class="ri-badge a">⚠ Dup</span>'
      :'<span class="ri-badge r">Unmatched</span>';
    var conf=r.confidence?Math.round(r.confidence*100)+'%':'—';
    var confCls=r.confidence>=0.85?'conf-high':r.confidence>=0.55?'conf-mid':'conf-low';
    return '<div class="result-item '+cls+'">'
      +'<span class="ri-pg">P'+r.page_number+'</span>'
      +'<div class="ri-body"><div class="ri-name">'+esc(r.filename||'Page '+r.page_number)+'</div>'
      +'<div class="ri-meta"><span class="ocr-chip '+confCls+'">🤖 '+conf+'</span>'
      +(r.extracted_id?'<span class="ocr-chip">ID: '+esc(r.extracted_id)+'</span>':'')
      +'</div></div>'+badge+'</div>';
  }).join('');
}

function showPdfSection(data){
  var sec=document.getElementById('pdfSection');if(!sec)return;
  sec.classList.remove('hidden');
  var groups={};
  (data.results||[]).forEach(function(r){
    if(r.status!=='success')return;
    var code=r.extracted_id||'unknown';
    if(!groups[code])groups[code]={code:code,name:r.extracted_name||code,pages:[],submission_id:r.submission_id||null};
    groups[code].pages.push(r);
    if(r.submission_id)groups[code].submission_id=r.submission_id;
  });
  _pdfData=groups;
  var keys=Object.keys(groups);
  var badge=document.getElementById('pdfCountBadge');
  if(badge)badge.textContent=keys.length+' student'+(keys.length!==1?'s':'');
  document.getElementById('pdfGrid').innerHTML=keys.map(function(code){
    var g=groups[code];var av=(g.name[0]||'?').toUpperCase();
    var viewUrl=g.submission_id?'/uploads/grade-submission/'+g.submission_id:'/student-directory';
    return '<div class="pdf-card"><div class="pdf-card-hd"><div class="pdf-av">'+av+'</div>'
      +'<div><div class="pdf-id">'+esc(g.name)+'</div>'
      +'<div class="pdf-pgct">'+g.pages.length+' page(s) — PDF auto-merged</div></div></div>'
      +'<div class="pdf-card-bd">'
      +'<button class="btn-card-dl ready" onclick="window.open(\''+viewUrl+'\',\'_blank\')">📄 View Paper</button>'
      +'</div></div>';
  }).join('');
}

function renderUnmatched(pages){
  var panel=document.getElementById('assignPanel');
  var body=document.getElementById('assignBody');
  var cnt=document.getElementById('assignCount');
  var banner=document.getElementById('autoAssignBanner');
  if(!panel||!body)return;
  panel.classList.remove('hidden');
  if(cnt)cnt.textContent=pages.length;
  _unmatchedPaths=pages.map(function(p){return p.file_path||'';});
  if(banner&&pages.length>1)banner.classList.remove('hidden');
  var stuOpts=(_students||[]).map(function(s){
    return '<option value="'+s.id+'">'+esc(s.name||'')+(s.student_code?' ('+esc(s.student_code)+')':'')+'</option>';
  }).join('');
  body.innerHTML=pages.map(function(page,idx){
    var ocrTxt=page.extracted_id?'OCR: '+esc(page.extracted_id):'No ID detected';
    var conf=page.confidence?Math.round(page.confidence*100)+'%':'—';
    return '<div class="unmatched-item" id="ui-'+idx+'">'
      +'<div class="ui-top"><div class="ui-thumb">🖼</div>'
      +'<div class="ui-info"><div class="ui-filename">Page '+(page.page_number||idx+1)+(page.filename?' — '+esc(page.filename):'')+'</div>'
      +'<div class="ui-ocr">🔍 '+ocrTxt+'</div>'
      +'<div class="ui-conf">Confidence: '+conf+'</div></div></div>'
      +'<div class="ui-sel-row"><select class="ui-select" id="usel-'+idx+'">'
      +'<option value="">— assign to student —</option>'+stuOpts+'</select>'
      +'<button class="btn-assign" onclick="assignPage('+idx+')">Assign</button></div></div>';
  }).join('');
}

async function quickAssignAll(){
  var sel=document.getElementById('quickAssignSelect');
  if(!sel||!sel.value){showToast('Select a student first.',false);return;}
  var studentId=parseInt(sel.value,10);
  if(!_unmatchedPaths.length){showToast('No unmatched pages.',false);return;}
  if(!confirm('Assign all '+_unmatchedPaths.length+' page(s) to this student?'))return;
  try{
    var res=await fetch('/api/exams/assign-page',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({exam_id:_examId,student_id:studentId,page_file:_unmatchedPaths[0]})});
    var data=await res.json();if(!res.ok)throw new Error(data.detail||'Assign failed');
    var pdfRes=await fetch('/api/exams/generate-pdf',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({exam_id:_examId,student_id:String(studentId),
        student_name:data.student_name,file_paths:_unmatchedPaths})});
    var pdfData=await pdfRes.json();if(!pdfRes.ok)throw new Error(pdfData.detail||'PDF failed');
    showToast('Assigned & PDF created for '+data.student_name,true);
    document.getElementById('viewPapersBanner').classList.add('show');
    markStudentStatus(data.student_code,'assigned',data.submission_id);
    _unmatchedPaths.forEach(function(_,idx){var row=document.getElementById('ui-'+idx);if(row)row.classList.add('done');});
    document.getElementById('autoAssignBanner').classList.add('hidden');
  }catch(err){showToast(err.message,false);}
}

async function assignPage(idx){
  var sel=document.getElementById('usel-'+idx);
  var filePath=_unmatchedPaths[idx]||'';
  if(!sel||!sel.value){showToast('Select a student first.',false);return;}
  if(!filePath){showToast('No file path stored.',false);return;}
  try{
    var res=await fetch('/api/exams/assign-page',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({exam_id:_examId,student_id:parseInt(sel.value,10),page_file:filePath})});
    var data=await res.json();if(!res.ok)throw new Error(data.detail||'Assign failed');
    showToast('Assigned to '+data.student_name,true);
    var row=document.getElementById('ui-'+idx);if(row)row.classList.add('done');
    markStudentStatus(data.student_code,'assigned',data.submission_id);
    document.getElementById('viewPapersBanner').classList.add('show');
  }catch(err){showToast(err.message,false);}
}

async function generateAllPDFs(){
  var btn=document.getElementById('genAllBtn');if(btn)btn.disabled=true;
  for(var code in _pdfData){if(_pdfData.hasOwnProperty(code))await generatePDF(code);}
  if(btn)btn.disabled=false;
}

async function generatePDF(code){
  var g=_pdfData[code];var btn=document.getElementById('pdfbtn-'+code);if(!g)return;
  if(btn){btn.className='btn-card-dl loading';btn.textContent='Generating…';}
  try{
    var res=await fetch('/api/exams/generate-pdf',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({exam_id:_examId,student_id:code,student_name:g.name,file_paths:g.pages.map(function(p){return p.file_path;})})});
    var data=await res.json();if(!res.ok)throw new Error(data.detail||'PDF failed');
    if(btn){btn.className='btn-card-dl ready';btn.textContent='⬇ Download';btn.onclick=function(){window.open(data.pdf_url,'_blank');};}
  }catch(err){
    if(btn){btn.className='btn-card-dl error';btn.textContent='Error';}
    showToast(err.message,false);
  }
}

function esc(s){
  return String(s===null||s===undefined?'':s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}