import os
import pytesseract
from pdf2image import convert_from_path
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
import fitz  # PyMuPDF
from utils import setup_tesseract
from summarization_utils import summarize_chunks

class PDFProcessor:
    def __init__(self, output_folder="output"):
        setup_tesseract(pytesseract)
        self._summarizer = None
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)
        
    @property
    def summarizer(self):
        if self._summarizer is None:
            print("Loading summarization model...")
            from transformers import pipeline
            self._summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
            
            # Reduce memory usage
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
        return self._summarizer

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
                    
            doc.close()
            
            # If no text found, try OCR
            if not text.strip():
                print("📸 No selectable text found, using OCR...")
                try:
                    images = convert_from_path(pdf_path, dpi=200)  # Lower DPI for memory
                    for i, img in enumerate(images):
                        try:
                            text += pytesseract.image_to_string(img) + "\n"
                            # Clear memory after each image
                            del img
                            if i % 5 == 0:  # More frequent garbage collection
                                import gc
                                gc.collect()
                        except Exception as e:
                            print(f"Error in OCR for page {i + 1}: {str(e)}")
                            continue
                except Exception as e:
                    print(f"Error in PDF to image conversion: {str(e)}")
            
            return text.strip() if text.strip() else None
            
        except Exception as e:
            print(f"Error extracting text: {e}")
            return None

    def summarize_text(self, text):
        if not text or not text.strip():
            return "No text to summarize"
            
        try:
            # Split text into chunks that the model can handle
            max_chunk_size = 1000
            chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
            
            # Process in small batches to save memory
            batch_size = 2
            summaries = []
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i+batch_size]
                try:
                    # Get summaries for this batch
                    batch_summaries = self.summarizer(
                        batch,
                        max_length=150,
                        min_length=30,
                        do_sample=False,
                        truncation=True
                    )
                    summaries.extend([s['summary_text'] for s in batch_summaries])
                    
                    # Clear memory
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                except Exception as e:
                    print(f"Error summarizing batch {i//batch_size + 1}: {str(e)}")
                    # Fallback: take first few sentences
                    for chunk in batch:
                        sentences = chunk.split('. ')
                        summaries.append('. '.join(sentences[:2]) + '.')
            
            return " ".join(summaries)
            
        except Exception as e:
            print(f"Error in summarization: {str(e)}")
            # Fallback: return first 200 characters
            return text[:200] + "..." if len(text) > 200 else text

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
