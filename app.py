import os
from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract

# ✅ For Docker: don't set Windows tesseract path
# Tesseract is already installed and accessible in Docker path
# Remove or comment out Windows-specific lines

# Create app
app = Flask(__name__)
CORS(app)

# Config
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
OUTPUT_FOLDER = os.path.join(os.getcwd(), 'output')
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, DOWNLOAD_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ Optional: Health check route for Render
@app.route('/healthz')
def healthz():
    return "OK", 200

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    filename = secure_filename(file.filename)
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], 'input', filename)
    os.makedirs(os.path.dirname(input_path), exist_ok=True)
    file.save(input_path)

    print(f"Tesseract path: {pytesseract.pytesseract.tesseract_cmd}")
    print(f"Image path: {input_path}")

    try:
        text = pytesseract.image_to_string(Image.open(input_path))
    except Exception as e:
        print("Error extracting text from image:", str(e))
        return f"Error processing image: {str(e)}", 500

    output_filename = os.path.splitext(filename)[0] + "_output.txt"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)

    return send_from_directory(OUTPUT_FOLDER, output_filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host='0.0.0.0', port=port)
