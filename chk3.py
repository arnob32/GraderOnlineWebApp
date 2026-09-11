import pathlib
js = pathlib.Path("app/static/JS/stamp_addon.js").read_text(encoding="utf-8", errors="replace")
print("Size:", len(js))
print("Has getActiveQuestion:", "getActiveQuestion" in js)
