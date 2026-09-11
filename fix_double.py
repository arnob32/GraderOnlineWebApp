import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")

# Remove the immediate bake call from doAddStamp - only bake on finish
old = """function doAddStamp(page,stamp){if(!stampData[page])stampData[page]=[];stampData[page].push(stamp);saveStamps();renderStampsForPage(page);setTimeout(function(){bakeStampsToCanvas(page);if(typeof _scheduleAutoSave==="function")_scheduleAutoSave(page);else if(typeof _autoSavePageToServer==="function")_autoSavePageToServer(page);},300);}"""

new = """function doAddStamp(page,stamp){if(!stampData[page])stampData[page]=[];stampData[page].push(stamp);saveStamps();renderStampsForPage(page);}"""

if old in content:
    content = content.replace(old, new)
    pathlib.Path("app/static/JS/stamp_addon.js").write_text(content, encoding="utf-8")
    print("Fixed - stamps no longer bake immediately")
else:
    print("Pattern not found")
    idx = content.find("function doAddStamp")
    print(repr(content[idx:idx+200]))
