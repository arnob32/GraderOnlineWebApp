import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

old = "function bakeStampsToCanvas(page){var ac=document.getElementById(\"annotationCanvas\");if(!ac)return;var stamps=stampData[page]||[];if(!stamps.length)return;var ctx=ac.getContext(\"2d\");var cw=ac.width,ch=ac.height;"

new = "function bakeStampsToCanvas(page){var ac=document.getElementById(\"annotationCanvas\");if(!ac)return;var stamps=stampData[page]||[];if(!stamps.length)return;var ctx=ac.getContext(\"2d\");var cw=ac.width,ch=ac.height;"

# Just check it exists
if old in content:
    print("bakeStampsToCanvas found")
else:
    print("not found")
    idx = content.find("bakeStampsToCanvas")
    print(repr(content[idx:idx+100]))
