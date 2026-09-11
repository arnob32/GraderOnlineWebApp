import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

old = """function hookFinishBtn(){var btn=document.getElementById("btnFinish");if(!btn){setTimeout(hookFinishBtn,600);return;}btn.addEventListener("click",function(){var page=(typeof currentPage!=="undefined")?currentPage:(typeof curPage!=="undefined"?curPage:1);var hasStamps=Object.keys(stampData).some(function(p){return (stampData[p]||[]).length>0;});if(!hasStamps)return;bakeStampsToCanvas(page);if(typeof _scheduleAutoSave==="function")_scheduleAutoSave(page);},true);}"""

new = """function hookFinishBtn(){var btn=document.getElementById("btnFinish");if(!btn){setTimeout(hookFinishBtn,600);return;}btn.addEventListener("click",function(){var hasStamps=Object.keys(stampData).some(function(p){return (stampData[p]||[]).length>0;});if(!hasStamps)return;Object.keys(stampData).forEach(function(p){var pg=parseInt(p);if((stampData[pg]||[]).length>0){bakeStampsToCanvas(pg);if(typeof _scheduleAutoSave==="function")_scheduleAutoSave(pg);}});},true);}"""

if old in content:
    content = content.replace(old, new)
    pathlib.Path("app/static/JS/stamp_addon.js").write_text(content, encoding="utf-8")
    print("Fixed - all pages baked on finish")
else:
    print("Not found")
