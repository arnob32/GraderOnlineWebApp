import pathlib, shutil

# 1. Copy stamp_addon.js
src = pathlib.Path('stamp_addon.js')
if not src.exists():
    print("ERROR: stamp_addon.js not found in current folder")
    exit()

dst = pathlib.Path('app/static/JS/stamp_addon.js')
shutil.copy(src, dst)
print("Copied stamp_addon.js ->", dst)
print("Size:", dst.stat().st_size, "bytes")

# 2. Patch grading_dashboard.html - add stamp buttons if not there
html_path = pathlib.Path('app/templates/grading_dashboard.html')
html = html_path.read_text(encoding='utf-8', errors='replace')

# Check stamp_addon script tag
if 'stamp_addon.js' not in html:
    old = '<script src="/static/JS/grading_dashboard.js'
    new = '<script src="/static/JS/stamp_addon.js"></script>\n<script src="/static/JS/grading_dashboard.js'
    if old in html:
        html = html.replace(old, new)
        print("Added stamp_addon.js script tag")

# Add stamp tool buttons if not present
if 'tool-mark-stamp' not in html:
    stamp_btns = (
        '\n      <div class="sep"></div>'
        '\n      <div class="atool" id="tool-mark-stamp" onclick="selectTool(\'mark-stamp\')" '
        'title="Click answer box to grade" '
        'style="background:#fee2e2;color:#991b1b;border-color:#fca5a5;">&#9999; Mark</div>'
        '\n      <div class="atool" id="tool-comment-stamp" onclick="selectTool(\'comment-stamp\')" '
        'title="Click answer box to add comment" '
        'style="background:#fefce8;color:#854d0e;border-color:#fde047;">&#128172; Comment</div>'
        '\n      <div class="atool" id="tool-tick-stamp" onclick="selectTool(\'tick-stamp\')" '
        'title="Click answer box to tick" '
        'style="background:#f0fdf4;color:#166534;border-color:#86efac;">&#10003; Tick</div>'
        '\n      <div class="atool" id="tool-cross-stamp" onclick="selectTool(\'cross-stamp\')" '
        'title="Click answer box to cross" '
        'style="background:#fff1f2;color:#be123c;border-color:#fda4af;">&#10007; Cross</div>'
    )
    # Find highlight tool and insert after
    idx = html.find('tool-highlight')
    if idx > 0:
        close = html.find('</div>', idx)
        if close > 0:
            html = html[:close+6] + stamp_btns + html[close+6:]
            print("Added stamp tool buttons to toolbar")

# Patch setPointerEvents to allow stamp tools
if '_st=["mark-stamp"' not in html and '_st=["mark-stamp"' not in pathlib.Path('app/static/JS/grading_dashboard.js').read_text(encoding='utf-8', errors='replace'):
    gd = pathlib.Path('app/static/JS/grading_dashboard.js')
    gd_content = gd.read_text(encoding='utf-8', errors='replace')
    old_ptr = 'function setPointerEvents(tool) {\n  const active = !!tool;'
    new_ptr = 'function setPointerEvents(tool) {\n  const _st=["mark-stamp","comment-stamp","tick-stamp","cross-stamp"];\n  const active = !!tool || _st.includes(activeTool);'
    if old_ptr in gd_content:
        gd_content = gd_content.replace(old_ptr, new_ptr)
        gd.write_text(gd_content, encoding='utf-8')
        print("Patched setPointerEvents in grading_dashboard.js")
    else:
        print("NOTE: setPointerEvents already patched or not found")

html_path.write_text(html, encoding='utf-8')
print("\nDone! Now run: uvicorn app.main:app --reload")