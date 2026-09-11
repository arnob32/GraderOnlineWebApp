import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

old = """function doNext(){if(idx>=pages.length){setTimeout(function(){stampData={};localStorage.removeItem("stamps_"+SUB_ID);if(stampLayer)stampLayer.innerHTML="";btn.disabled=false;btn.textContent="Finish Marking";if(typeof finishMarking==="function")finishMarking();},500);return;}var pg=parseInt(pages[idx]);bakeStampsToCanvas(pg);captureCanvasToAnnotations(pg);if(typeof _autoSavePageToServer==="function"){_autoSavePageToServer(pg).then(function(){idx++;setTimeout(doNext,400);});}else{if(typeof _scheduleAutoSave==="function")_scheduleAutoSave(pg);idx++;setTimeout(doNext,800);}}doNext();"""

new = """function doNext(){if(idx>=pages.length){setTimeout(function(){stampData={};localStorage.removeItem("stamps_"+SUB_ID);if(stampLayer)stampLayer.innerHTML="";btn.disabled=false;btn.textContent="Finish Marking";if(typeof finishMarking==="function")finishMarking();},500);return;}var pg=parseInt(pages[idx]);
  // Navigate to page first, then bake after render completes
  if(typeof renderPage==="function"){
    renderPage(pg).then(function(){
      setTimeout(function(){
        bakeStampsToCanvas(pg);
        captureCanvasToAnnotations(pg);
        if(typeof _autoSavePageToServer==="function"){
          _autoSavePageToServer(pg).then(function(){idx++;setTimeout(doNext,600);});
        }else{if(typeof _scheduleAutoSave==="function")_scheduleAutoSave(pg);idx++;setTimeout(doNext,1000);}
      },300);
    });
  }else{bakeStampsToCanvas(pg);captureCanvasToAnnotations(pg);if(typeof _autoSavePageToServer==="function"){_autoSavePageToServer(pg).then(function(){idx++;setTimeout(doNext,400);});}else{idx++;setTimeout(doNext,800);}}
}doNext();"""

if old in content:
    content = content.replace(old, new)
    pathlib.Path("app/static/JS/stamp_addon.js").write_text(content, encoding="utf-8")
    print("Fixed - navigate to page before baking")
else:
    print("Not found")
    idx2 = content.find("function doNext")
    print(repr(content[idx2:idx2+200]))
