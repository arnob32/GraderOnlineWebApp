import pathlib
content = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")
print("Has bakeStampsToCanvas call in doAddStamp:", "bakeStampsToCanvas" in content[content.find("function doAddStamp"):content.find("function doAddStamp")+200])
print("doAddStamp function:")
idx = content.find("function doAddStamp")
print(repr(content[idx:idx+150]))
