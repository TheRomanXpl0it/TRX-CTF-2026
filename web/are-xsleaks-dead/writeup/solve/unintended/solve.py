import sys
import uvicorn
from fastapi import FastAPI, Header
from fastapi.responses import HTMLResponse
from pyngrok import ngrok

PORT = sys.argv[1] if len(sys.argv) > 1 else 9999

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def filler():
    return open("filler.html").read()

@app.get("/chunk", response_class=HTMLResponse)
async def get_chunk(size: int, x: str):
    headers = {"Cache-Control": "public, max-age=31536000, immutable"}
    return HTMLResponse(content="A"*size, headers=headers)

if __name__ == "__main__":
    #tunnel = ngrok.connect(PORT, "tcp")
    #ngrok_url = tunnel.public_url.replace("tcp://", "http://")
    #print(f"{ngrok_url=}")
    uvicorn.run("solve:app", host="0.0.0.0", port=PORT, reload=True)
