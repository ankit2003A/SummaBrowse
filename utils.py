import os

tesseract_paths = [
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