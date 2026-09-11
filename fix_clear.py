import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

old = """function hookFinishBtn(){var btn=document.getElementById("btnFinish");if(!btn){setTimeout(hookFinishBtn,600);return;}btn.addEventListener("click",function(){var hasStamps=Object.keys(stampData).some(function(p){return (stampData[p]||[]).length>0;});if(!hasStamps)return;Object.keys(stampData).forEach(function(p){var pg=parseInt(p);if((stampData[pg]||[]).length>0){bakeStampsToCanvas(pg);if(typeof _scheduleAutoSave==="function")_scheduleAutoSave(pg);}});},true);}"""

new = """function hookFinishBtn(){var btn=document.getElementById("btnFinish");if(!btn){setTimeout(hookFinishBtn,600);return;}btn.addEventListener("click",function(){var hasStamps=Object.keys(stampData).some(function(p){return (stampData[p]||[]).length>0;});if(!hasStamps)return;Object.keys(stampData).forEach(function(p){var pg=parseInt(p);if((stampData[pg]||[]).length>0){bakeStampsToCanvas(pg);if(typeof _scheduleAutoSave==="function")_scheduleAutoSave(pg);}});setTimeout(function(){stampData={};localStorage.removeItem("stamps_"+SUB_ID);if(stampLayer)stampLayer.innerHTML="";},1500);},true);}"""

if old in content:
    content = content.replace(old, new)
    pathlib.Path("app/static/JS/stamp_addon.js").write_text(content, encoding="utf-8")
    print("Fixed")
else:
    print("Not found")
    idx = content.find("hookFinishBtn")
    print(repr(content[idx:idx+300]))
