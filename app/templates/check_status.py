from dotenv import load_dotenv
load_dotenv()
import requests

r = requests.get('http://127.0.0.1:8000/api/student-directory')
d = r.json()
print('Papers count:', len(d))
for p in d:
    print('  sub=' + str(p['submission_id']) + ' status=' + str(p['status']) + ' student=' + str(p['student_name']))