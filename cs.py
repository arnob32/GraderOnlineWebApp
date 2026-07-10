from dotenv import load_dotenv
load_dotenv()
import requests
r = requests.get('http://127.0.0.1:8000/api/student-directory')
d = r.json()
print('Papers:', len(d))
for p in d:
    print(p.get('submission_id'), p.get('status'), p.get('student_name'))
