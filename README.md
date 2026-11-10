# SummaBrowse

**SummaBrowse** is a Flask app that extracts and summarizes content from PDFs, images and videos.

Live demo: https://summabrowse.onrender.com

It combines OCR, YouTube captions, audio transcription and AI summarization to turn long documents and videos into clear summaries.

---

## Features

- **PDFs:** selectable-text extraction with an OCR fallback for scanned PDFs (PyMuPDF + Tesseract)
- **Images:** OCR with Tesseract
- **YouTube:** summarizes from the video's captions (no download needed)
- **Video/audio uploads:** audio extracted with ffmpeg, transcribed with Gemini (or local Whisper)
- **Summary length:** short, medium or detailed
- **Summarization fallback chain:** Gemini → local BART model (optional) → pure-Python extractive summarizer; the UI shows which engine produced each summary
- **Privacy:** uploads get random names and are deleted right after processing; summaries are never stored on the server (downloads are generated in the browser)
- **Abuse protection:** per-IP rate limits, upload size and video length limits, restricted CORS
- Docker-ready, deployed on Render

---

## Project structure

| File | Purpose |
| --- | --- |
| `app.py` | Flask routes, upload handling, rate limiting, error handling |
| `app_factory.py` | Singleton Flask app and lazily loaded processors |
| `pdf_processor.py` | PDF text extraction and OCR fallback |
| `image_processor.py` | Image OCR |
| `video_processor.py` | YouTube captions, ffmpeg audio extraction, transcription |
| `utils.py` | Summarization chain, Gemini client, Markdown cleanup |
| `templates/index.html` | Front end |
| `requirements.txt` | Lightweight runtime dependencies (used in Docker/Render) |
| `requirements-local.txt` | Optional offline models (BART, Whisper, yt-dlp) |

---

## Running locally

Prerequisites: Python 3.10+, `tesseract` and `ffmpeg` on your PATH.

```sh
git clone https://github.com/ankit2003A/summabrowse.git
cd summabrowse
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:

```sh
GEMINI_API_KEY=your-key-here
```

Run it:

```sh
python app.py
```

Then open http://localhost:10000.

### Fully offline mode (optional)

```sh
pip install -r requirements-local.txt
```

Then add to `.env`:

```sh
ENABLE_LOCAL_MODELS=true       # BART summaries + Whisper transcription
ENABLE_YTDLP_FALLBACK=true     # download audio for YouTube videos without captions
```

These models need several GB of RAM, so they're disabled on Render.

---

## Docker

```sh
docker build -t summabrowse .
docker run -p 10000:10000 -e GEMINI_API_KEY=your-key-here summabrowse
```

---

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `GEMINI_API_KEY` | – | Enables Gemini summaries and transcription |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model name |
| `MAX_UPLOAD_MB` | `25` | Maximum upload size |
| `MAX_VIDEO_MINUTES` | `30` | Maximum video/audio length |
| `MAX_OCR_PAGES` | `20` | Maximum scanned PDF pages to OCR |
| `PROCESS_RATE_LIMIT` | `10 per hour;3 per minute` | Per-IP limit for documents |
| `VIDEO_RATE_LIMIT` | `5 per hour;2 per minute` | Per-IP limit for videos |
| `ALLOWED_ORIGINS` | – | Comma-separated origins allowed to call the API from other sites |
| `ENABLE_LOCAL_MODELS` | `false` | Use local BART/Whisper |
| `ENABLE_YTDLP_FALLBACK` | `false` | Download YouTube audio when a video has no captions |
| `WEB_CONCURRENCY` | `1` | Gunicorn workers |

---

## Deploying to Render

The repo includes a `render.yaml` blueprint (Docker runtime, free plan, `/healthz` health check). Set `GEMINI_API_KEY` in the Render dashboard.

## Author

Built by [Ankit Verma](https://www.linkedin.com/in/ankit-verma01).
