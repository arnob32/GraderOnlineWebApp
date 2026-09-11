import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

old = """function hookFinishBtn(){var btn=document.getElementById("btnFinish");if(!btn){setTimeout(hookFinishBtn,600);return;}btn.addEventListener("click",function(){var hasStamps=Object.keys(stampData).some(function(p){return (stampData[p]||[]).length>0;});if(!hasStamps)return;Object.keys(stampData).forEach(function(p){var pg=parseInt(p);if((stampData[pg]||[]).length>0){bakeStampsToCanvas(pg);if(typeof _scheduleAutoSave==="function")_scheduleAutoSave(pg);}});setTimeout(function(){stampData={};localStorage.removeItem("stamps_"+SUB_ID);if(stampLayer)stampLayer.innerHTML="";},1500);},true);}"""

new = """function hookFinishBtn(){var btn=document.getElementById("btnFinish");if(!btn){setTimeout(hookFinishBtn,600);return;}btn.addEventListener("click",function(e){var hasStamps=Object.keys(stampData).some(function(p){return (stampData[p]||[]).length>0;});if(!hasStamps)return;e.stopImmediatePropagation();e.preventDefault();btn.disabled=true;btn.textContent="Saving marks...";var pages=Object.keys(stampData).filter(function(p){return (stampData[p]||[]).length>0;});var idx=0;function doNext(){if(idx>=pages.length){setTimeout(function(){stampData={};localStorage.removeItem("stamps_"+SUB_ID);if(stampLayer)stampLayer.innerHTML="";btn.disabled=false;btn.textContent="Finish Marking";if(typeof finishMarking==="function")finishMarking();},500);return;}var pg=parseInt(pages[idx]);bakeStampsToCanvas(pg);if(typeof _autoSavePageToServer==="function"){_autoSavePageToServer(pg).then(function(){idx++;setTimeout(doNext,400);});}else{if(typeof _scheduleAutoSave==="function")_scheduleAutoSave(pg);idx++;setTimeout(doNext,800);}}doNext();},true);}"""

if old in content:
    content = content.replace(old, new)
    pathlib.Path("app/static/JS/stamp_addon.js").write_text(content, encoding="utf-8")
    print("Fixed - sequential save before finish")
else:
    print("Not found")
    idx = content.find("hookFinishBtn")
    print(repr(content[idx:idx+200]))
