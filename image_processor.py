import os
import pytesseract
from PIL import Image
from utils import setup_tesseract, summarize_text

class TextExtractorAndSummarizer:
    def __init__(self):
        setup_tesseract(pytesseract)

    def extract_text_from_image(self, image_path):
        """
        Extract text from an image using Tesseract OCR
        """
        try:
            if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
                raise Exception(f"Tesseract not found at: {pytesseract.pytesseract.tesseract_cmd}")

            # Open the image
            image = Image.open(image_path)
            
            # Extract text from the image
            extracted_text = pytesseract.image_to_string(image)
            
            if not extracted_text.strip():
                print("Warning: No text was extracted from the image")
                return None
                
            return extracted_text.strip()
        except Exception as e:
            print(f"Error extracting text from image: {str(e)}")
            print(f"Image path: {image_path}")
            print(f"Tesseract path: {pytesseract.pytesseract.tesseract_cmd}")
            return None

    def generate_summary(self, text):
        """
        Generate a professional summary using the centralized utility.
        """
        return summarize_text(text)
 