import secrets
from pathlib import Path
from pydantic import BaseModel
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates("templates/")
notes_by_session: dict[str, list[dict[str, object]]] = {}

class Note(BaseModel):
    content: str

def get_session_notes(request: Request) -> tuple[str, bool, list[dict[str, object]]]:
    session_id = request.cookies.get("sid")
    is_new = not session_id
    if is_new:
        session_id = secrets.token_hex(16)
    return session_id, is_new, notes_by_session.setdefault(session_id, [])

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, q: str = Query(default="")) -> Response:
    session_id, is_new, notes = get_session_notes(request)
    query = q.strip().lower()
    filtered_notes = [
        note for note in notes if query in str(note["content"]).lower()
    ] if query else notes
    response = templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "notes": filtered_notes, "q": q},
        status_code=200 if filtered_notes else 404,
    )
    if is_new:
        response.set_cookie("sid", session_id, httponly=True, samesite="lax")
    return response

@app.post("/notes")
async def create_note(request: Request, payload: Note) -> JSONResponse:
    session_id, is_new, notes = get_session_notes(request)
    notes.append({"id": len(notes) + 1, "content": payload.content})
    response = JSONResponse({"ok": True})
    if is_new:
        response.set_cookie("sid", session_id, httponly=True, samesite="lax")
    return response
