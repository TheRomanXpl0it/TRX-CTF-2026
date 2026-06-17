import os
import time
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000/")
FLAG = os.getenv("FLAG", "TRX{fake_flag_fake_flag_fake_flag_}")
CHROME_BIN = os.getenv("CHROME_BIN", "/usr/bin/chromium")
CHROMEDRIVER = os.getenv("CHROMEDRIVER", "/usr/bin/chromedriver")
VISIT_SECONDS = float(os.getenv("VISIT_SECONDS", "300"))

class Report(BaseModel):
    url: str

def visit(url: str) -> None:
    assert len(FLAG) == 35
    options = Options()
    options.binary_location = CHROME_BIN
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--js-flags=--jitless --no-expose-wasm")
    driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=options)
    try:
        driver.get(BASE_URL)
        driver.find_element(By.ID, "content").send_keys(FLAG)
        driver.find_element(By.CSS_SELECTOR, "#note-form button").click()

        notes_tab = driver.current_window_handle
        driver.switch_to.new_window("tab")
        driver.switch_to.window(notes_tab)
        driver.close()

        driver.switch_to.window(driver.window_handles[0])
        driver.get(url)
        time.sleep(VISIT_SECONDS)
    finally:
        try: driver.quit()
        except Exception: pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates("templates/")
limiter = Limiter(key_func=lambda request: "global")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"request": request})

@app.post("/report")
@limiter.limit("3/minute")
async def report(request: Request, background_tasks: BackgroundTasks, payload: Report) -> dict[str, bool]:
    if not payload.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="invalid report url")
    background_tasks.add_task(visit, payload.url)
    return {"ok": True}
