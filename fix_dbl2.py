import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

old = """document.addEventListener("DOMContentLoaded",function(){loadStamps();initStampLayer();initStampClick();initQTracker();hookPageRender();hookFinishBtn();setTimeout(function(){renderStampsForPage((typeof curPage!=="undefined")?curPage:1);recalcTotalFromStamps();},2000);});"""

new = """document.addEventListener("DOMContentLoaded",function(){
  // Clear old stamps if paper was already finished/sent
  if(typeof isFinished!=="undefined"&&isFinished){
    localStorage.removeItem("stamps_"+SUB_ID);
    stampData={};
  } else {
    loadStamps();
  }
  initStampLayer();initStampClick();initQTracker();hookPageRender();hookFinishBtn();
  setTimeout(function(){renderStampsForPage((typeof curPage!=="undefined")?curPage:1);recalcTotalFromStamps();},2000);
});"""

if old in content:
    content = content.replace(old, new)
    pathlib.Path("app/static/JS/stamp_addon.js").write_text(content, encoding="utf-8")
    print("Fixed")
else:
    print("Not found")
    idx = content.find("DOMContentLoaded")
    print(repr(content[idx:idx+200]))
