import os
import uuid
import yt_dlp
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Serve static (user-provided assets live in app/static)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/scan")
def scan_video(url: str):
    # Temporary file with unique name (no collisions, easy cleanup)
    temp_filename = f"{uuid.uuid4()}.mp4"

    ydl_opts = {
        "outtmpl": temp_filename,
        "format": "best",
        # Don't keep fragments around, be quiet in logs
        "quiet": True,
        "nopart": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Collect *direct* stream URLs for all formats (if present)
            video_links = []
            for fmt in info.get("formats", []):
                u = fmt.get("url")
                if u and u not in video_links:
                    video_links.append(u)

        # Best-effort cleanup of the downloaded file
        try:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
        except Exception:
            pass

        return JSONResponse(content={"links": video_links})

    except Exception as e:
        # Ensure cleanup even on failures
        try:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
        except Exception:
            pass
        return JSONResponse(content={"error": str(e)}, status_code=500)
