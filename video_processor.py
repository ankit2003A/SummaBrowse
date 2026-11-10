"""
Video summarization.

- YouTube: fetch the video's captions with youtube-transcript-api (no download, no
  Whisper, works on a 512 MB instance). Optional yt-dlp audio fallback for local use.
- Local video/audio: extract a small mono MP3 with ffmpeg, then transcribe it with
  Gemini (default) or a local Whisper model (ENABLE_LOCAL_MODELS=true).
"""
import base64
import json
import logging
import os
import re
import subprocess
import tempfile
import uuid
from urllib.parse import urlparse, parse_qs

from utils import summarize, gemini_generate, length_instruction

logger = logging.getLogger(__name__)

MAX_VIDEO_MINUTES = int(os.environ.get("MAX_VIDEO_MINUTES", "30"))
TRANSCRIPT_LANGUAGES = [l.strip() for l in os.environ.get("TRANSCRIPT_LANGUAGES", "en,en-US,en-GB,hi").split(",") if l.strip()]
WORK_DIR = os.path.join(tempfile.gettempdir(), "summabrowse_media")
os.makedirs(WORK_DIR, exist_ok=True)

YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def env_flag(name):
    return os.environ.get(name, "false").lower() == "true"


def extract_youtube_id(url):
    """Return the 11-char video id from any common YouTube URL form, or None."""
    url = url.strip()
    if YOUTUBE_ID_RE.match(url):
        return url
    parsed = urlparse(url if "://" in url else "https://" + url)
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    candidate = None
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host in ("youtube.com", "music.youtube.com", "youtube-nocookie.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
                candidate = parts[1]
    return candidate if candidate and YOUTUBE_ID_RE.match(candidate) else None


def error(message, status=422):
    return {"error": message, "status": status}


class VideoProcessor:
    def __init__(self):
        self._whisper_model = None

    # ------------------------------------------------------------------ YouTube
    def fetch_youtube_transcript(self, video_id):
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        transcripts = api.list(video_id)
        try:
            transcript = transcripts.find_transcript(TRANSCRIPT_LANGUAGES)
        except Exception:
            # Fall back to whatever captions exist (manual first, then auto-generated).
            transcript = next(iter(transcripts))
        fetched = transcript.fetch()
        return " ".join(s.text.replace("\n", " ") for s in fetched if s.text.strip())

    def process_youtube(self, url, length="medium"):
        video_id = extract_youtube_id(url)
        if not video_id:
            return error("That doesn't look like a valid YouTube video URL.", 400)

        from youtube_transcript_api import (
            TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, RequestBlocked, IpBlocked,
        )

        blocked, no_captions = False, False
        try:
            transcript = self.fetch_youtube_transcript(video_id)
        except (TranscriptsDisabled, NoTranscriptFound, StopIteration):
            transcript = None
            no_captions = True
        except VideoUnavailable:
            return error("This video is unavailable or private.")
        except (RequestBlocked, IpBlocked):
            logger.warning("YouTube blocked transcript request for %s", video_id)
            transcript, blocked = None, True
        except Exception:
            logger.exception("Transcript fetch failed for %s", video_id)
            transcript, blocked = None, True
        else:
            no_captions = False

        if transcript:
            summary, engine = summarize(transcript, length)
            return {"summary": summary, "engine": engine, "source": "captions"}

        # Captions unavailable (no captions, or YouTube is blocking this server):
        # let Gemini watch the public video directly from its URL.
        if os.environ.get("GEMINI_API_KEY"):
            try:
                summary = self.summarize_youtube_with_gemini(video_id, length)
                return {"summary": summary, "engine": "gemini", "source": "video"}
            except Exception as e:
                logger.error("Gemini YouTube summarization failed for %s: %s", video_id, e)

        # Optional audio download fallback (off by default; YouTube blocks most
        # datacenter IPs, so this is mainly useful when running locally).
        if env_flag("ENABLE_YTDLP_FALLBACK"):
            audio_path = None
            try:
                audio_path = self.download_youtube_audio(video_id)
                return self.summarize_audio(audio_path, length, source="audio")
            except Exception:
                logger.exception("yt-dlp fallback failed for %s", video_id)
            finally:
                self._remove(audio_path)

        if blocked:
            return error("YouTube is temporarily blocking requests from this server. Please try again later, or upload the video file instead.", 503)
        if no_captions:
            return error("This video has no captions and couldn't be summarized. Make sure it's public, or upload the video file instead.")
        return error("Couldn't get a transcript for this video.")

    def summarize_youtube_with_gemini(self, video_id, length):
        prompt = (
            "Summarize this video. " + length_instruction(length) +
            " Use Markdown formatting. Do not include raw HTML. "
            "Start directly with the summary itself: no preamble such as 'Here is a summary'."
        )
        return gemini_generate([
            {"file_data": {"file_uri": f"https://www.youtube.com/watch?v={video_id}"}},
            {"text": prompt},
        ], timeout=280)

    def download_youtube_audio(self, video_id):
        import yt_dlp

        out_base = os.path.join(WORK_DIR, f"yt_{uuid.uuid4().hex}")
        opts = {
            "format": "bestaudio/best",
            "outtmpl": out_base + ".%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "match_filter": yt_dlp.utils.match_filter_func(f"duration <= {MAX_VIDEO_MINUTES * 60}"),
        }
        if os.path.exists("cookies.txt"):
            opts["cookiefile"] = "cookies.txt"
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
            downloaded = ydl.prepare_filename(info)
        return self.to_small_mp3(downloaded, remove_source=True)

    # ------------------------------------------------------------------ Local files
    def process_local(self, path, length="medium"):
        duration = self.probe_duration(path)
        if duration is None:
            return error("Couldn't read this file. Please upload a valid video or audio file.", 400)
        if duration > MAX_VIDEO_MINUTES * 60:
            return error(f"Videos longer than {MAX_VIDEO_MINUTES} minutes aren't supported yet.", 400)

        audio_path = None
        try:
            audio_path = self.to_small_mp3(path)
            return self.summarize_audio(audio_path, length, source="audio")
        finally:
            self._remove(audio_path)

    def summarize_audio(self, audio_path, length, source):
        try:
            transcript = self.transcribe(audio_path)
        except RuntimeError as e:
            logger.error("%s", e)
            return error("Transcription isn't available right now. Please try again later.", 503)
        if not transcript or not transcript.strip():
            return error("No speech could be transcribed from this file.")
        summary, engine = summarize(transcript, length)
        return {"summary": summary, "engine": engine, "source": source}

    # ------------------------------------------------------------------ Media helpers
    @staticmethod
    def probe_duration(path):
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
                capture_output=True, text=True, timeout=30, check=True,
            )
            return float(json.loads(out.stdout)["format"]["duration"])
        except Exception as e:
            logger.warning("ffprobe failed: %s", e)
            return None

    @staticmethod
    def to_small_mp3(path, remove_source=False):
        """Mono 16 kHz 32 kbps MP3: ~14 MB/hour, small enough to send inline to Gemini."""
        out = os.path.join(WORK_DIR, f"audio_{uuid.uuid4().hex}.mp3")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000",
                 "-b:a", "32k", "-t", str(MAX_VIDEO_MINUTES * 60), out],
                capture_output=True, timeout=600, check=True,
            )
        finally:
            if remove_source:
                VideoProcessor._remove(path)
        return out

    def transcribe(self, audio_path):
        if os.environ.get("GEMINI_API_KEY"):
            try:
                with open(audio_path, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("ascii")
                return gemini_generate([
                    {"text": "Transcribe this audio verbatim. Output only the transcript text."},
                    {"inline_data": {"mime_type": "audio/mp3", "data": audio_b64}},
                ], timeout=240)
            except Exception as e:
                logger.error("Gemini transcription failed: %s", e)

        if env_flag("ENABLE_LOCAL_MODELS"):
            try:
                if self._whisper_model is None:
                    import whisper
                    logger.info("Loading Whisper (tiny)...")
                    self._whisper_model = whisper.load_model("tiny")
                return self._whisper_model.transcribe(audio_path)["text"]
            except Exception as e:
                logger.error("Whisper transcription failed: %s", e)

        raise RuntimeError("No transcription engine available (set GEMINI_API_KEY or ENABLE_LOCAL_MODELS=true).")

    @staticmethod
    def _remove(path):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                logger.warning("Could not remove %s: %s", path, e)
