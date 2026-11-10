import os
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tesseract
# ---------------------------------------------------------------------------
tesseract_paths = [
    '/usr/bin/tesseract',
    '/usr/local/bin/tesseract',
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Tesseract-OCR\tesseract.exe',
]


def find_tesseract():
    for path in tesseract_paths:
        if os.path.exists(path):
            return path
    return None


def setup_tesseract(pytesseract):
    tesseract_path = find_tesseract()
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    else:
        logger.warning("Tesseract not found in common locations; relying on PATH.")


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------
def clean_markdown(text):
    """Convert Markdown to plain text for the downloadable .txt file."""
    text = re.sub(r'\*\*+(.*?)\*\*+', r'\1', text)
    text = re.sub(r'\*+(.*?)\*+', r'\1', text)
    text = re.sub(r'(?m)^#{1,6}\s+(.*?)\s*$', r'\1', text)
    text = re.sub(r'(?m)^[-*_]{3,}\s*$', r'', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'\n{3,}', r'\n\n', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_API_BASE = os.environ.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta")
# Cap on characters sent to the LLM so huge PDFs don't blow the request size / timeout.
MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", "120000"))

LENGTHS = {
    "short": {"instruction": "Write a short summary of about 3-5 bullet points.", "sentences": 3, "bart_max": 80},
    "medium": {"instruction": "Write a structured summary with a one-line overview, the main points as bullets, and a short conclusion.", "sentences": 6, "bart_max": 150},
    "long": {"instruction": "Write a detailed, structured summary with headings, covering every key concept, argument, figure and conclusion.", "sentences": 12, "bart_max": 250},
}


def normalize_length(length):
    return length if length in LENGTHS else "medium"


def gemini_headers():
    return {
        "Content-Type": "application/json",
        # Send the key as a header, not a URL query param, so it never lands in access logs.
        "x-goog-api-key": os.environ.get("GEMINI_API_KEY", ""),
    }


def gemini_generate(parts, timeout=60):
    """Call Gemini generateContent. Returns text or raises."""
    import requests

    url = f"{GEMINI_API_BASE}/models/{GEMINI_MODEL}:generateContent"
    response = requests.post(url, headers=gemini_headers(), json={"contents": [{"parts": parts}]}, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"Gemini API returned {response.status_code}: {response.text[:300]}")
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def length_instruction(length):
    return LENGTHS[normalize_length(length)]["instruction"]


def _summarize_gemini(text, length):
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS] + "\n\n[Text truncated for length]"
    prompt = (
        "You are a professional summary generator. Analyze the following text and summarize it. "
        f"{LENGTHS[length]['instruction']} Use Markdown formatting. Do not include raw HTML. "
        "Start directly with the summary itself: no preamble such as 'Here is a summary'.\n\n"
        f"Text:\n{text}"
    )
    return gemini_generate([{"text": prompt}])


_summarizer = None


def _summarize_transformers(text, length):
    global _summarizer
    from transformers import pipeline  # noqa: imported lazily; heavy

    if _summarizer is None:
        logger.info("Loading local BART summarization model...")
        _summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

    max_len = LENGTHS[length]["bart_max"]
    chunks = [text[i:i + 1000] for i in range(0, min(len(text), 20000), 1000)]
    summaries = []
    for i in range(0, len(chunks), 2):
        batch = chunks[i:i + 2]
        out = _summarizer(batch, max_length=max_len, min_length=min(30, max_len // 2), do_sample=False, truncation=True)
        summaries.extend(s["summary_text"] for s in out)
    return " ".join(summaries)


STOPWORDS = {
    'the', 'and', 'that', 'this', 'with', 'from', 'your', 'have', 'about', 'they', 'will', 'been', 'were',
    'which', 'their', 'there', 'would', 'could', 'should', 'into', 'than', 'then', 'them', 'these', 'those',
    'also', 'what', 'when', 'where', 'while', 'some', 'such', 'only', 'other', 'more', 'most', 'very',
}


def _summarize_extractive(text, length):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    target = LENGTHS[length]["sentences"]
    if len(sentences) <= target:
        return text.strip()

    words = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', text.lower()) if w not in STOPWORDS]
    freq = Counter(words)
    scores = []
    for s in sentences:
        s_words = re.findall(r'\b[a-zA-Z]{4,}\b', s.lower())
        # Normalise by length so long sentences don't always win.
        scores.append(sum(freq.get(w, 0) for w in s_words) / (len(s_words) ** 0.5 or 1))

    top = sorted(range(len(sentences)), key=lambda i: scores[i], reverse=True)[:target]
    top.sort()
    return " ".join(sentences[i] for i in top)


def summarize(text, length="medium"):
    """
    Summarize text, trying Gemini -> local transformer -> extractive fallback.
    Returns (summary, engine) so the UI can show which engine produced it.
    """
    length = normalize_length(length)
    if not text or not text.strip():
        return "No text to summarize.", "none"

    if os.environ.get("GEMINI_API_KEY"):
        try:
            return _summarize_gemini(text, length), "gemini"
        except Exception as e:
            logger.error("Gemini summarization failed: %s", e)

    if os.environ.get("ENABLE_LOCAL_MODELS", "false").lower() == "true":
        try:
            return _summarize_transformers(text, length), "bart"
        except Exception as e:
            logger.error("Local transformer summarization failed: %s", e)

    return _summarize_extractive(text, length), "extractive"


def summarize_text(text, length="medium"):
    """Backwards-compatible helper returning only the summary string."""
    return summarize(text, length)[0]
