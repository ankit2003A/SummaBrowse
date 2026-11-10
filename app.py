import os
import uuid
import logging
import tempfile

from dotenv import load_dotenv
load_dotenv()

from flask import render_template, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from app_factory import app_factory, app
from utils import summarize, clean_markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("summabrowse")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# Uploads only ever live in a temp folder and are deleted right after processing.
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(tempfile.gettempdir(), "summabrowse_uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

DOC_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".mp3", ".wav", ".m4a"}

# CORS: only allow the origins you list (comma-separated). Same-origin requests from
# the bundled UI don't need CORS at all, so the default is to allow nothing extra.
allowed_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if allowed_origins:
    CORS(app, origins=allowed_origins)

# Rate limiting protects the Gemini quota and the small Render instance.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)
PROCESS_LIMIT = os.environ.get("PROCESS_RATE_LIMIT", "10 per hour;3 per minute")
VIDEO_LIMIT = os.environ.get("VIDEO_RATE_LIMIT", "5 per hour;2 per minute")


def save_upload(file, allowed_extensions):
    """Save an upload under a random name. Returns (path, ext) or raises ValueError."""
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in allowed_extensions:
        raise ValueError(f"Unsupported file type '{ext or 'unknown'}'.")
    path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}{ext}")
    file.save(path)
    return path, ext


def remove_quietly(path):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError as e:
            logger.warning("Could not remove %s: %s", path, e)


def summary_payload(summary, engine, extra=None):
    payload = {
        "summary": summary,
        # Plain-text version for the client-side download; nothing is stored on the server.
        "summary_text": clean_markdown(summary),
        "engine": engine,
    }
    if extra:
        payload.update(extra)
    return payload


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(RequestEntityTooLarge)
def too_large(_e):
    return jsonify({"error": f"File is too large. The limit is {MAX_UPLOAD_MB} MB."}), 413


@app.errorhandler(429)
def rate_limited(_e):
    return jsonify({"error": "Too many requests. Please wait a bit and try again."}), 429


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/healthz")
@limiter.exempt
def healthz():
    return "OK", 200


@app.route("/")
def index():
    return render_template(
        "index.html",
        max_upload_mb=MAX_UPLOAD_MB,
        max_video_minutes=int(os.environ.get("MAX_VIDEO_MINUTES", "30")),
    )


@app.route("/process", methods=["POST"])
@limiter.limit(PROCESS_LIMIT)
def process():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    length = request.form.get("length", "medium")
    input_path = None
    try:
        input_path, ext = save_upload(file, DOC_EXTENSIONS)

        if ext == ".pdf":
            extracted_text = app_factory.get_pdf_processor().extract_text_with_ocr(input_path)
        else:
            extracted_text = app_factory.get_image_processor().extract_text_from_image(input_path)

        if not extracted_text:
            return jsonify({"error": "No readable text was found in this file."}), 422

        summary, engine = summarize(extracted_text, length)
        return jsonify(summary_payload(summary, engine, {"extracted_text": extracted_text}))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error processing document")
        return jsonify({"error": "Something went wrong while processing the file. Please try again."}), 500
    finally:
        remove_quietly(input_path)


@app.route("/process_video", methods=["POST"])
@limiter.limit(VIDEO_LIMIT)
def process_video():
    video_processor = app_factory.get_video_processor()
    input_path = None
    try:
        if request.is_json:
            data = request.get_json(silent=True) or {}
            video_source = (data.get("video_source") or "").strip()
            length = data.get("length", "medium")
            if not video_source:
                return jsonify({"error": "Please provide a YouTube URL."}), 400
            result = video_processor.process_youtube(video_source, length)
        else:
            file = request.files.get("video_file")
            if not file or file.filename == "":
                return jsonify({"error": "No video file selected."}), 400
            length = request.form.get("length", "medium")
            input_path, _ = save_upload(file, VIDEO_EXTENSIONS)
            result = video_processor.process_local(input_path, length)

        if "error" in result:
            status = result.pop("status", 422)
            return jsonify({"error": result["error"]}), status
        return jsonify(summary_payload(result["summary"], result["engine"], {"source": result.get("source")}))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error processing video")
        return jsonify({"error": "Something went wrong while processing the video. Please try again."}), 500
    finally:
        remove_quietly(input_path)


def main():
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
