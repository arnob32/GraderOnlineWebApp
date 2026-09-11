content = open("app/static/JS/stamp_addon.js", encoding="utf-8", errors="replace").read()
print("Size:", len(content))
print("Has doAddStamp:", "doAddStamp" in content)
print("Has getActiveQuestion:", "getActiveQuestion" in content)
