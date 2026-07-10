from dotenv import load_dotenv
load_dotenv()
import requests
s = requests.Session()
r = s.post("http://127.0.0.1:8000/auth/login", data={"email":"raju@gmail.com","password":"admin123"}, allow_redirects=True)
print("Login:", r.status_code, r.url)
print("Cookies:", list(s.cookies.keys()))
r2 = s.get("http://127.0.0.1:8000/student-directory")
print("Page size:", len(r2.text))
print("Has loadPapers:", "loadPapers" in r2.text)
print("Has fetch:", "fetch" in r2.text)
print("Has tableBody:", "tableBody" in r2.text)
