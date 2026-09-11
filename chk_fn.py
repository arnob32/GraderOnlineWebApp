import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

old = """setTimeout(function(){stampData={};localStorage.removeItem("stamps_"+SUB_ID);if(stampLayer)stampLayer.innerHTML="";btn.disabled=false;btn.textContent="Finish Marking";if(typeof finishMarking==="function")finishMarking();},500);return;}"""

new = """setTimeout(function(){
  stampData={};localStorage.removeItem("stamps_"+SUB_ID);
  if(stampLayer)stampLayer.innerHTML="";
  btn.disabled=false;btn.textContent="Finish Marking";
  // Call finishMarking but skip its annotation save — our stamps are already saved
  if(typeof finishMarking==="function")finishMarking();
},500);return;}"""

if old in content:
    content = content.replace(old, new)
    pathlib.Path("app/static/JS/stamp_addon.js").write_text(content, encoding="utf-8")
    print("OK")
else:
    print("Not found - checking doNext")
    idx = content.find("finishMarking")
    print(repr(content[max(0,idx-50):idx+100]))
