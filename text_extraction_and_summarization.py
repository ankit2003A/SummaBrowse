import os
import pytesseract
from PIL import Image

# Set Tesseract path for Windows
tesseract_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Tesseract-OCR\tesseract.exe'
]

def find_tesseract():
    """Find Tesseract executable"""
    for path in tesseract_paths:
        if os.path.exists(path):
            return path
    return None

class TextExtractorAndSummarizer:
    def __init__(self):
        # Set Tesseract path for Windows
        tesseract_path = find_tesseract()
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            print("Warning: Tesseract not found in common locations.")
            print("Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
            print("Expected locations:")
            for path in tesseract_paths:
                print(f"- {path}")

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

    def generate_summary(self, text, max_length=130, min_length=30):
        """
        Generate a simple summary by taking the first few sentences.
        (For future: can integrate a transformer-based summarizer for higher accuracy.)
        """
        try:
            # Split text into sentences
            sentences = text.split('.')
            
            # Remove empty sentences
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return "No text to summarize."
            
            # Take first few sentences as summary (30% of total sentences or at least 2 sentences)
            num_sentences = max(2, min(len(sentences), max(min_length // 30, len(sentences) // 3)))
            summary = '. '.join(sentences[:num_sentences]) + '.'
            
            return summary.strip()
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return None

def main():
    # Initialize the extractor and summarizer
    extractor = TextExtractorAndSummarizer()
    
    # Get image path from user
    image_path = input("Enter the path to your image: ")
    
    if not os.path.exists(image_path):
        print("Error: Image file not found!")
        return
    
    # Extract text from image
    print("\nExtracting text from image...")
    extracted_text = extractor.extract_text_from_image(image_path)
    
    if extracted_text:
        print("\nExtracted Text:")
        print("-" * 50)
        print(extracted_text)
        print("-" * 50)
        
        # Generate summary
        print("\nGenerating summary...")
        summary = extractor.generate_summary(extracted_text)
        
        if summary:
            print("\nSummary:")
            print("-" * 50)
            print(summary)
            print("-" * 50)
        else:
            print("Failed to generate summary.")
    else:
        print("Failed to extract text from the image.")

if __name__ == "__main__":
    main() 