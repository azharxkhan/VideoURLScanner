import os
import re
import cv2
import pytesseract
import subprocess
import requests
from urllib.parse import urlparse
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.requests import Request

# ---------------- Configuration ----------------
VIDEO_FILE = "video.mp4"
TEXT_FILE = "extracted_text.txt"
URL_DOMAINS = ["com", "net", "org", "io", "co", "edu", "gov", "info", "biz", "me"]
TESSERACT_CMD = r"/usr/bin/tesseract"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------- Functions ----------------
def delete_old_files():
    for file in [VIDEO_FILE, TEXT_FILE]:
        if os.path.exists(file):
            os.remove(file)

def download_video(url, output_file=VIDEO_FILE):
    try:
        subprocess.run(
            ["yt-dlp", "-f", "bestvideo+bestaudio", "--merge-output-format", "mp4", "-o", output_file, url],
            check=True
        )
        return output_file
    except subprocess.CalledProcessError:
        return None

def preprocess_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return thresh

def extract_urls_from_text(text_list):
    urls = set()
    url_pattern = r"(https?://[a-zA-Z0-9.-]+\.(?:{})(?:/[^\s]*)?)".format("|".join(URL_DOMAINS))
    plain_pattern = r"\b[a-zA-Z0-9.-]+\.(?:{})\b".format("|".join(URL_DOMAINS))
    for line in text_list:
        urls.update(re.findall(url_pattern, line))
        urls.update(re.findall(plain_pattern, line))
    return list(urls)

def check_domain_exists(domain):
    parsed = urlparse(domain if domain.startswith("http") else "http://" + domain)
    url = f"http://{parsed.netloc}" if parsed.netloc else f"http://{parsed.path}"
    try:
        r = requests.get(url, timeout=5)
        return r.status_code < 500
    except requests.RequestException:
        return False

def extract_text_from_video(video_file):
    cap = cv2.VideoCapture(video_file)
    frame_count = 0
    all_text = []
    detected_urls = set()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        processed = preprocess_frame(frame)
        text = pytesseract.image_to_string(processed, config="--oem 3 --psm 6").strip()
        if text:
            all_text.append(f"[Frame {frame_count}] {text}")
            urls = extract_urls_from_text([text])
            detected_urls.update(urls)
        frame_count += 24
    cap.release()
    with open(TEXT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(all_text))
    return detected_urls

# ---------------- Routes ----------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "results": None})

@app.post("/scan", response_class=HTMLResponse)
def scan_video(request: Request, video_url: str = Form(...)):
    delete_old_files()
    video_file = download_video(video_url)
    if not video_file:
        return templates.TemplateResponse("index.html", {"request": request, "results": "❌ Could not download video"})
    urls = extract_text_from_video(video_file)
    results = {}
    for u in urls:
        results[u] = check_domain_exists(u)
    return templates.TemplateResponse("index.html", {"request": request, "results": results})
