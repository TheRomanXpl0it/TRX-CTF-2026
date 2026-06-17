#!/usr/bin/env python3
import time
import tempfile
import asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

app = FastAPI()

async def save_upload(upload: UploadFile, dst: Path) -> None:
    size = 0
    with dst.open("wb") as out:
        while True:
            chunk = await upload.read(1* 1024 * 1024)
            if not chunk: break
            size += len(chunk)
            if size > 1 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Extension too large (max 1MB)")
            out.write(chunk)
    await upload.close()

def run_webdriver(ext_path: str) -> None:
    opts = Options()
    opts.binary_location = "/usr/bin/firefox"
    opts.add_argument("-headless")
    opts.set_preference("javascript.options.wasm", False)
    opts.set_preference("javascript.options.baselinejit", False)
    opts.set_preference("javascript.options.ion", False)
    opts.set_preference("javascript.options.asmjs", False)
    service = Service(executable_path="/usr/bin/geckodriver")
    driver = webdriver.Firefox(options=opts, service=service)
    try:
        addon_id = driver.install_addon(ext_path, temporary=True)
        time.sleep(60)
        for p in Path("/tmp/").glob("*.xpi"): p.unlink(missing_ok=True)
        driver.uninstall_addon(addon_id)
    except Exception:
        pass
    finally:
        driver.quit()

@app.post("/visit")
async def visit(extension: UploadFile = File(...)):
    if not extension.filename:
        raise HTTPException(status_code=400, detail="No extension uploaded")

    with tempfile.TemporaryDirectory(prefix="bot_", dir="/tmp") as td:
        ext_path = Path(td) / "extension.xpi"
        await save_upload(extension, ext_path)
        await asyncio.to_thread(run_webdriver, str(ext_path))

    return {"status": "success"}
