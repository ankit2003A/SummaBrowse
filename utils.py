import os

tesseract_paths = [
    '/usr/bin/tesseract',
    '/usr/local/bin/tesseract',
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',  # Your Tesseract installation path
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Tesseract-OCR\tesseract.exe'
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
        print("Warning: Tesseract not found in common locations.")
        print("Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("Expected locations:")
        for path in tesseract_paths:
            print(f"- {path}")

def clean_markdown(text):
    import re
    # 1. Remove bold/italic markers (**bold** or *italic*)
    text = re.sub(r'\*\*+(.*?)\*\*+', r'\1', text)
    text = re.sub(r'\*+(.*?)\*+', r'\1', text)
    # 2. Remove headers (### Header -> Header)
    text = re.sub(r'(?m)^#{1,6}\s+(.*?)\s*$', r'\1', text)
    # 3. Remove horizontal rules (---)
    text = re.sub(r'(?m)^[-*_]{3,}\s*$', r'', text)
    # 4. Remove links ([text](url) -> text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # 5. Clean up multiple empty lines
    text = re.sub(r'\n{3,}', r'\n\n', text)
    return text.strip()

# Lazy-loaded Transformers check and pipeline
try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

_summarizer = None

def get_summarizer():
    global _summarizer
    if _summarizer is None and HAS_TRANSFORMERS:
        print("Loading summarization model...")
        from transformers import pipeline
        _summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        
        # Reduce memory usage
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
    return _summarizer

def summarize_text(text):
    if not text or not text.strip():
        return "No text to summarize"

    # 1. Try Gemini API first (highly professional, fast, lightweight, and memory-safe)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print("Using cloud-based Gemini API for professional summarization...")
        import requests
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.5-flash:generateContent?key={api_key}"
            headers = {'Content-Type': 'application/json'}
            prompt = (
                "You are a professional summary generator. Please analyze the following text and provide "
                "a professional, structured summary highlighting key concepts, main points, and conclusions.\n\n"
                f"Text:\n{text}"
            )
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                res_json = response.json()
                summary = res_json['candidates'][0]['content']['parts'][0]['text']
                return summary.strip()
            else:
                print(f"Gemini API returned status code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")

    # 2. Try local transformer-based model (if transformers and torch are installed)
    if HAS_TRANSFORMERS:
        if os.environ.get("RENDER") == "true":
            print("Running on Render: Skipping local transformer model to prevent Out-of-Memory (OOM) crashes.")
        else:
            print("Using local Hugging Face transformer model for summarization...")
            try:
                summarizer_pipeline = get_summarizer()
            if summarizer_pipeline:
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
                        batch_summaries = summarizer_pipeline(
                            batch,
                            max_length=150,
                            min_length=30,
                            do_sample=False,
                            truncation=True
                        )
                        summaries.extend([s['summary_text'] for s in batch_summaries])
                        
                        # Clear memory
                        try:
                            import torch
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()
                        except ImportError:
                            pass
                        
                    except Exception as e:
                        print(f"Error summarizing batch: {str(e)}")
                        # Fallback for this chunk
                        for chunk in batch:
                            sentences = chunk.split('. ')
                            summaries.append('. '.join(sentences[:2]) + '.')
                
                return " ".join(summaries)
        except Exception as e:
            print(f"Error in local transformer summarization: {str(e)}")

    # 3. Smart Pure-Python Extractive Fallback (requires NO packages, runs instantly)
    print("Using smart term-frequency extractive summarizer fallback...")
    try:
        import re
        from collections import Counter
        # Split text into sentences
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) <= 4:
            return text
        
        # Tokenize and count word frequencies
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        stopwords = {'the', 'and', 'a', 'to', 'of', 'in', 'is', 'that', 'it', 'for', 'on', 'with', 'as', 'this', 'but', 'by', 'not', 'or', 'be', 'are', 'from', 'at', 'an', 'your', 'have', 'about', 'they', 'will', 'been', 'were'}
        filtered_words = [w for w in words if w not in stopwords]
        word_frequencies = Counter(filtered_words)
        
        # Score sentences
        sentence_scores = []
        for s in sentences:
            score = 0
            s_words = re.findall(r'\b[a-zA-Z]{4,}\b', s.lower())
            for w in s_words:
                if w in word_frequencies:
                    score += word_frequencies[w]
            sentence_scores.append(score)
        
        # Pick the top sentences (e.g. 20% of sentences or at least 3, at most 8)
        num_summary_sentences = max(3, min(len(sentences) // 5, 8))
        
        # Get indices of top scoring sentences
        top_indices = sorted(range(len(sentence_scores)), key=lambda i: sentence_scores[i], reverse=True)[:num_summary_sentences]
        # Sort indices chronologically to maintain document flow
        top_indices.sort()
        
        return " ".join([sentences[i] for i in top_indices])
    except Exception as e:
        print(f"Error in simple extractive fallback: {str(e)}")

    # 4. Final basic fallback (first few sentences)
    print("Using basic fallback summarizer...")
    sentences = text.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    num_sentences = max(2, min(len(sentences), max(2, len(sentences) // 3)))
    return '. '.join(sentences[:num_sentences]) + '.'