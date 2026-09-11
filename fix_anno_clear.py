import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

# Clear anno localStorage for pages that have stamps before finishMarking runs
# so finishMarking does not re-save old annotations over our stamp PNGs
old = "stampData={};localStorage.removeItem(\"stamps_\"+SUB_ID);"
new = """stampData={};localStorage.removeItem("stamps_"+SUB_ID);
  // Remove annotation cache for stamped pages so finishMarking does not overwrite stamp PNGs
  try{var stored=JSON.parse(localStorage.getItem("anno_"+SUB_ID)||"{}");pages.forEach(function(p){delete stored[p];});localStorage.setItem("anno_"+SUB_ID,JSON.stringify(stored));}catch(e){}"""

if old in content:
    content = content.replace(old, new)
    pathlib.Path("app/static/JS/stamp_addon.js").write_text(content, encoding="utf-8")
    print("Fixed - cleared anno cache for stamped pages")
else:
    print("Not found")
