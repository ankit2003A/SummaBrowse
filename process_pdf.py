import os
import pytesseract
from pdf2image import convert_from_path
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
import fitz  # PyMuPDF

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

class PDFProcessor:
    def __init__(self, output_folder="output"):
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

        # Initialize the summarizer model
        self.summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

        # Ensure the output folder exists
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)

    def extract_text_with_ocr(self, pdf_path):
        """Extract text from a PDF using PyMuPDF for digital PDFs, fallback to OCR if necessary."""
        text = ""
        try:
            # Try fast extraction with PyMuPDF
            doc = fitz.open(pdf_path)
            for page in doc:
                extracted_text = page.get_text()
                if extracted_text:
                    text += extracted_text + "\n"
            doc.close()

            # If no text found, fallback to OCR
            if not text.strip():
                print("📸 No selectable text found, using OCR...")
                images = convert_from_path(pdf_path)
                for img in images:
                    text += pytesseract.image_to_string(img) + "\n"

            return text.strip() if text.strip() else None
        except Exception as e:
            print(f"Error extracting text: {e}")
            return None

    def summarize_text(self, text):
        """Summarize the extracted text using a quantized transformer model."""
        try:
            max_chunk = 512  # Use larger chunk for efficiency
            chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
            summarized_chunks = []

            for chunk in chunks:
                summary = self.summarizer(chunk, max_length=200, min_length=50, do_sample=False)
                summarized_chunks.append(summary[0]['summary_text'])

            return "\n".join(summarized_chunks)
        except Exception as e:
            print(f"Error summarizing text: {str(e)}")
            return None

    def extract_keywords(self, text, num_keywords=10):
        """Extract top keywords using TF-IDF."""
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            keywords = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
            return [keyword for keyword, _ in keywords[:num_keywords]]
        except Exception as e:
            print(f"Error extracting keywords: {str(e)}")
            return []

    def save_summary_to_file(self, summary, keywords, output_file):
        """Save structured summary and keywords to a file."""
        try:
            with open(output_file, "w", encoding="utf-8") as file:
                file.write("📄 **Document Summary**\n")
                file.write("=" * 50 + "\n\n")
                file.write(summary + "\n\n")
                file.write("✨ **Key Topics & Keywords** ✨\n")
                file.write("-" * 50 + "\n")
                file.write(", ".join(keywords) + "\n")
            print(f"✅ Summary saved successfully to {output_file}")
        except Exception as e:
            print(f"Error saving summary to file: {str(e)}")

    def process_pdf(self, pdf_file_path):
        """Complete process: Extract text, summarize, extract keywords, and save."""
        try:
            print("📥 Extracting text from PDF...")
            text = self.extract_text_with_ocr(pdf_file_path)

            if text:
                extracted_text_file = os.path.join(self.output_folder, "extracted_text.txt")
                with open(extracted_text_file, "w", encoding="utf-8") as file:
                    file.write(text)
                print(f"✅ Extracted text saved to {extracted_text_file}")

                print("📖 Summarizing text...")
                summary = self.summarize_text(text)

                print("🔍 Extracting keywords...")
                keywords = self.extract_keywords(text)

                summary_file = os.path.join(self.output_folder, "summary.txt")
                self.save_summary_to_file(summary, keywords, summary_file)

                print(f"📄 Summary and keywords saved to {summary_file}")
                return summary, keywords
            else:
                print("⚠️ No valid text found in the PDF! Check your file.")
                return None, None
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return None, None

def main():
    # Example usage
    processor = PDFProcessor()
    pdf_file_path = input("Enter the path to your PDF file: ")

    if os.path.exists(pdf_file_path):
        processor.process_pdf(pdf_file_path)
    else:
        print("Error: PDF file not found!")

if __name__ == "__main__":
    main()
