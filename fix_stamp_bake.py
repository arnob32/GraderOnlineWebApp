content = open('app/static/JS/stamp_addon.js', encoding='utf-8', errors='replace').read()

old = """function addStamp(page, stamp) {
  if (!stampData[page]) stampData[page] = [];
  stampData[page].push(stamp);
  saveStamps();
  renderStampsForPage(page);
}"""

new = """function addStamp(page, stamp) {
  if (!stampData[page]) stampData[page] = [];
  stampData[page].push(stamp);
  saveStamps();
  renderStampsForPage(page);
  // Bake immediately to canvas so autosave picks it up like a pen stroke
  setTimeout(function() {
    bakeStampsToCanvas(page);
    if (typeof _scheduleAutoSave === "function") _scheduleAutoSave(page);
    else if (typeof _autoSavePageToServer === "function") _autoSavePageToServer(page);
  }, 200);
}"""

if old in content:
    content = content.replace(old, new)
    open('app/static/JS/stamp_addon.js', 'w', encoding='utf-8').write(content)
    print("Fixed - stamps bake immediately to canvas")
else:
    print("Pattern not found")
    idx = content.find("function addStamp")
    print(repr(content[idx:idx+200]))
