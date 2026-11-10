import io
import os
import logging

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from utils import setup_tesseract, summarize_text

logger = logging.getLogger(__name__)

# OCR is slow and memory-hungry on a small instance, so cap the pages we OCR.
MAX_OCR_PAGES = int(os.environ.get("MAX_OCR_PAGES", "20"))
MAX_PDF_PAGES = int(os.environ.get("MAX_PDF_PAGES", "300"))


class PDFProcessor:
    def __init__(self):
        setup_tesseract(pytesseract)

    def extract_text_with_ocr(self, pdf_path):
        """Extract selectable text; fall back to OCR for scanned PDFs."""
        with fitz.open(pdf_path) as doc:
            page_count = min(len(doc), MAX_PDF_PAGES)
            parts = []
            for page_num in range(page_count):
                try:
                    parts.append(doc.load_page(page_num).get_text())
                except Exception as e:
                    logger.warning("Text extraction failed on page %d: %s", page_num + 1, e)
            text = "\n".join(p for p in parts if p)

            if not text.strip():
                logger.info("No selectable text found; running OCR on up to %d pages", MAX_OCR_PAGES)
                parts = []
                for page_num in range(min(len(doc), MAX_OCR_PAGES)):
                    try:
                        pix = doc.load_page(page_num).get_pixmap(dpi=150)
                        with Image.open(io.BytesIO(pix.tobytes("png"))) as img:
                            parts.append(pytesseract.image_to_string(img))
                    except Exception as e:
                        logger.warning("OCR failed on page %d: %s", page_num + 1, e)
                text = "\n".join(parts)

        return text.strip() or None

    def summarize_text(self, text, length="medium"):
        return summarize_text(text, length)
