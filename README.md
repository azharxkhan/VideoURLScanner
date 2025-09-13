# Video URL Scanner (OCR) — Pro

A production-ready FastAPI app that:
- Downloads a video (yt-dlp)
- Scans frames with OCR (Tesseract via OpenCV) to extract text
- Pulls domains/URLs from detected text
- Checks which links are reachable (tries HTTPS, then HTTP)
- Deletes the downloaded video after processing
- Responsive UI with fixed backgrounds: `rain-bar.gif` (desktop), `cozy-aesthetic.gif` (mobile)
- Easter egg: type `azhar` in the input and it shows a love message 💙

## Project Structure

```
.
├─ app.py
├─ index.html
├─ static/
│  ├─ rain-bar.gif              # (add if not already present)
│  └─ cozy-aesthetic.gif        # (add if not already present)
├─ requirements.txt
├─ Dockerfile
├─ render.yaml
├─ .dockerignore
└─ README.md
```

> If your `static/` folder was provided in `app.zip`, it's been copied into this project. Ensure your GIFs exist at the paths above for the backgrounds to display.

## Local Run (Docker)

```bash
docker build -t video-url-scanner-pro .
docker run -p 8000:8000 video-url-scanner-pro
# open http://localhost:8000
```

## Deploy on Render

- Push this folder to GitHub/GitLab.
- In Render: **New Web Service** → connect repo → it reads `render.yaml` automatically.
- The app binds to `$PORT` and runs `uvicorn app:app`.

## Notes

- Tesseract path is set to `/usr/bin/tesseract` (works in this Docker image).
- Free hosting tiers may kill requests after ~90s. Use short videos or a paid plan for long processing.
- OCR regex extracts both `https://domain.tld/...` and plain `domain.tld` patterns across TLDs listed in code.
