import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

old = "function captureCanvasToAnnotations(pg){var ac=document.getElementById(\"annotationCanvas\");if(ac&&typeof annotations!==\"undefined\")annotations[pg]=ac.toDataURL(\"image/png\");}"

new = """function captureCanvasToAnnotations(pg){
  var ac=document.getElementById("annotationCanvas");
  if(!ac||typeof annotations==="undefined")return;
  var stamps=stampData[pg]||[];
  if(!stamps.length)return;
  // Create composite: existing annotation + baked stamps
  var comp=document.createElement("canvas");
  comp.width=ac.width;comp.height=ac.height;
  var ctx=comp.getContext("2d");
  // Draw existing annotation if any
  if(annotations[pg]){
    var img=new Image();
    img.src=annotations[pg];
    ctx.drawImage(img,0,0);
  }
  // Draw stamps on top
  var stampCtx=ac.getContext("2d");
  ctx.drawImage(ac,0,0);
  annotations[pg]=comp.toDataURL("image/png");
}"""

if old in content:
    content = content.replace(old, new)
    pathlib.Path("app/static/JS/stamp_addon.js").write_text(content, encoding="utf-8")
    print("Fixed - composite annotation+stamps")
else:
    print("Not found")
    idx = content.find("captureCanvasToAnnotations")
    print(repr(content[idx:idx+100]))
