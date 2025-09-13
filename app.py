from fastapi import FastAPI, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os, re, subprocess, cv2, pytesseract, requests
from urllib.parse import urlparse

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------- Config ----------
VIDEO_FILE = "video.mp4"
TEXT_FILE = "extracted_text.txt"
URL_DOMAINS = ["com", "net", "org", "io", "co", "edu", "gov", "info", "biz", "me"]
FRAME_SKIP = 10
TESSERACT_CMD = r"/usr/bin/tesseract"   # inside Docker
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


# ---------- Helpers ----------
def delete_old_files():
    for file in [VIDEO_FILE, TEXT_FILE]:
        if os.path.exists(file):
            try:
                os.remove(file)
            except Exception:
                pass


def download_video(url, output_file=VIDEO_FILE):
    try:
        subprocess.run(
            [
                "yt-dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
                "-o", output_file,
                url,
            ],
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
    host = parsed.netloc if parsed.netloc else parsed.path

    # Try HTTPS first, then HTTP
    for scheme in ["https", "http"]:
        url = f"{scheme}://{host}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 500:
                return True
        except requests.RequestException:
            continue
    return False


def extract_text_from_video(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        return []

    detected_urls = set()
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % FRAME_SKIP == 0:
            processed = preprocess_frame(frame)
            text = pytesseract.image_to_string(processed, config="--oem 3 --psm 6").strip()
            if text:
                urls = extract_urls_from_text([text])
                detected_urls.update(urls)
        frame_count += 1
    cap.release()
    return detected_urls


def process_video(video_url):
    delete_old_files()
    video_file = download_video(video_url)
    if not video_file:
        return "<h2>❌ Could not download video</h2>"

    urls = extract_text_from_video(video_file)
    if not urls:
        delete_old_files()
        return "<h2>⚠️ No URLs/domains found in video text</h2>"

    results_html = "<h2>Results:</h2><ul>"
    for url in urls:
        live = check_domain_exists(url)
        results_html += f"<li>{url} --> {'LIVE ✅' if live else 'NOT FOUND ❌'}</li>"
    results_html += "</ul>"

    delete_old_files()
    return results_html


# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse("index.html")


@app.post("/scan", response_class=HTMLResponse)
def scan_video(background_tasks: BackgroundTasks, video_url: str = Form(...)):
    # synchronous processing; short videos recommended on free hosts
    result_html = process_video(video_url)
    return HTMLResponse(result_html)
