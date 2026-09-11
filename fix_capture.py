import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

# After baking, capture canvas to annotations so _autoSavePageToServer picks it up
old = "function doNext(){if(idx>=pages.length){"

new = "function captureCanvasToAnnotations(pg){var ac=document.getElementById(\"annotationCanvas\");if(ac&&typeof annotations!==\"undefined\")annotations[pg]=ac.toDataURL(\"image/png\");}function doNext(){if(idx>=pages.length){"

old2 = "bakeStampsToCanvas(pg);if(typeof _autoSavePageToServer"
new2 = "bakeStampsToCanvas(pg);captureCanvasToAnnotations(pg);if(typeof _autoSavePageToServer"

if old in content:
    content = content.replace(old, new)
    print("Added captureCanvasToAnnotations")
else:
    print("doNext not found")

if old2 in content:
    content = content.replace(old2, new2)
    print("Added capture call before save")
else:
    print("bakeStamps call not found")

pathlib.Path("app/static/JS/stamp_addon.js").write_text(content, encoding="utf-8")
print("Done")
