# SummaBrowse

**SummaBrowse** is a modern Flask application for extracting and summarizing content from PDFs, images, and videos.

It combines OCR, transcription, and AI-powered summarization to deliver clean, professional summaries from uploaded documents and media.

---

## 🚀 Key Features

- PDF text extraction with selectable-text support and OCR fallback
- Image OCR using Tesseract
- Video transcription using Whisper for local files and YouTube URLs
- Multi-layer summarization:
  - Gemini API if configured
  - Local Hugging Face transformer model
  - Pure-Python extractive fallback
- Downloadable summary `.txt` outputs
- Docker-ready deployment

---

## 🧩 Project Structure

- `app.py` — Flask routes, upload/download handling, and UI endpoints
- `app_factory.py` — singleton app container and lazy-loaded processors
- `pdf_processor.py` — PDF parsing, OCR, and summary generation
- `image_processor.py` — image OCR and summary generation
- `video_processor.py` — video/audio extraction, transcription, and summarization
- `utils.py` — shared utilities, Tesseract setup, markdown cleanup, and summarization orchestration
- `templates/index.html` — front-end upload UI
- `Dockerfile` — Docker build configuration
- `requirements.txt` — Python dependencies

---

## ⚙️ Prerequisites

- Python 3.10+
- Tesseract OCR installed and available on the system path
- `ffmpeg` installed for video/audio conversion
- Optional: `GEMINI_API_KEY` for cloud-based summarization

---

## 💻 Local Installation

1. Clone the repository:


git clone https://github.com/ankit2003A/SummaBrowse.git
cd SummaBrowse


2. Create and activate a virtual environment:


python -m venv .venv
.venv\Scripts\Activate.ps1 # PowerShell

# or

.venv\Scripts\activate.bat # Command Prompt


3. Install Python dependencies:


pip install -r requirements.txt


4. Install system tools:

- Windows: install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
- Linux/macOS: install `tesseract` and `ffmpeg` via your package manager

5. Run the app:


python app.py


6. Open the web app:


http://localhost:10000


---

## 🐳 Docker Deployment

Build the Docker image:


docker build -t summa-browse .


Run the container:


docker run -p 10000:10000 summa-browse


Then visit:


http://localhost:10000


---

## ☁️ Deploying to Production

This project is ready for deployment on Render, Railway, Fly.io, or any Docker-compatible environment.

Recommended environment variables:

- `HOST=0.0.0.0`
- `PORT=10000`
- `GEMINI_API_KEY` (optional)

---

## 📌 Usage

### Documents

- Upload a PDF or image file
- The app extracts text and produces a summary
- Download the summary as a `.txt` file

### Video

- Submit a YouTube URL or upload a local video file
- The app extracts audio, transcribes the speech, and summarizes the transcript
- Download the generated summary

> Note: YouTube downloading may require `cookies.txt` for restricted videos or additional browser cookies support.

---

## 🗂️ Output Locations

- `uploads/` — uploaded files
- `output/` — generated summary files
- `downloads/` — temporary audio/video files

---

## 💡 Tips

- Ensure Tesseract and FFmpeg are installed and working before processing files.
- For the best summarization results, provide clean text or clear audio.
- If you use YouTube processing, keep the video URL valid and accessible.

---
