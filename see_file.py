import pathlib
p = pathlib.Path("app/static/JS/stamp_addon.js")
print("Current first 80 chars:")
print(repr(p.read_text(encoding="utf-8", errors="replace")[:80]))
