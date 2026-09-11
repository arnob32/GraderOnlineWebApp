import urllib.request
import os

url = "https://raw.githubusercontent.com/arnob32/GraderOnlineWebApp/main/app/static/JS/stamp_addon.js"
try:
    urllib.request.urlretrieve(url, "app/static/JS/stamp_addon.js")
    print("Downloaded from GitHub")
except Exception as e:
    print("Failed:", e)
