from dotenv import load_dotenv
load_dotenv()
from app.main import app
for route in app.routes:
    if hasattr(route, "path") and "student" in route.path.lower():
        print(route.path, getattr(route, "methods", ""))
