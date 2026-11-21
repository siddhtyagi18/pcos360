import urllib.request
import urllib.error
import json

routes = [
    "/api/health",
    "/api/auth/login",
    "/api/pcoscope/analysis",
    "/api/ai/chat",
    "/api/health-context/me",
]

base = "https://pcos360-backend.onrender.com"
print(f"Testing routes on {base}:")

for r in routes:
    url = base + r
    req = urllib.request.Request(url, headers={"User-Agent": "PCOS360-QA/1.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"  {r} -> HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        print(f"  {r} -> HTTP {e.code} ({e.reason})")
    except Exception as ex:
        print(f"  {r} -> Error: {ex}")

