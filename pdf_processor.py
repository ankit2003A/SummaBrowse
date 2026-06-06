import os
import pytesseract
import fitz  # PyMuPDF
from utils import setup_tesseract, summarize_text

class PDFProcessor:
    def __init__(self, output_folder="output"):
        setup_tesseract(pytesseract)
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)

    def extract_text_with_ocr(self, pdf_path):
        text = ""
        try:
            # First try to extract text directly
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    extracted_text = page.get_text()
                    if extracted_text:
                        text += extracted_text + "\n"
                    # Clear memory after each page
                    import gc
                    del page
                    gc.collect()
                except Exception as e:
                    print(f"Error on page {page_num + 1}: {str(e)}")
                    continue
                    
            # If no text found, try OCR using PyMuPDF to convert pages to images
            if not text.strip():
                print("[OCR] No selectable text found, using OCR (via PyMuPDF)...")
                import io
                from PIL import Image
                for page_num in range(len(doc)):
                    try:
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(dpi=150)  # Lower DPI for memory efficiency
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        
                        text += pytesseract.image_to_string(img) + "\n"
                        
                        # Clear memory after each page
                        del img
                        del pix
                        if page_num % 5 == 0:
                            import gc
                            gc.collect()
                    except Exception as e:
                        print(f"Error in OCR for page {page_num + 1}: {str(e)}")
                        continue
            
            doc.close()
            return text.strip() if text.strip() else None
            
        except Exception as e:
            print(f"Error extracting text: {e}")
            raise e

    def summarize_text(self, text):
        return summarize_text(text)

