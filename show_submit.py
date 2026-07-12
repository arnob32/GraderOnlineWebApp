content = open('app/static/JS/create_exam.js', encoding='utf-8', errors='replace').read()
idx = content.find('async function submitExam')
print(content[idx:idx+1800])
