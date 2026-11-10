import logging

import pytesseract
from PIL import Image

from utils import setup_tesseract, summarize_text

logger = logging.getLogger(__name__)


class TextExtractorAndSummarizer:
    def __init__(self):
        setup_tesseract(pytesseract)

    def extract_text_from_image(self, image_path):
        """Extract text from an image using Tesseract OCR. Returns None if nothing is found."""
        try:
            with Image.open(image_path) as image:
                extracted_text = pytesseract.image_to_string(image)
        except Exception as e:
            logger.error("Image OCR failed: %s", e)
            return None
        return extracted_text.strip() or None

    def generate_summary(self, text, length="medium"):
        return summarize_text(text, length)
