import pathlib
p = pathlib.Path('app/static/JS/stamp_addon.js')
print("Current size:", p.stat().st_size)
print("First 200 chars:")
print(p.read_text(encoding="utf-8", errors="replace")[:200])
