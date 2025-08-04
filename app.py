import os
from flask import Flask, render_template, request, jsonify, send_file
import uuid
from werkzeug.utils import secure_filename
from text_extraction_and_summarization import TextExtractorAndSummarizer
from process_pdf import PDFProcessor
from process_video import YouTubeAudioProcessor  # Import the video processor
from moviepy import VideoFileClip
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["chrome-extension://ldemhkhknojajajjfomnhcpmdcfilggh"])

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), UPLOAD_FOLDER)
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Initialize the video processor
video_processor = YouTubeAudioProcessor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Ensure unique filename if it already exists
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(file_path):
        filename = f"{base}_{counter}{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        counter += 1

    file.save(file_path)

    try:
        text, summary = None, None

        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            summarizer = TextExtractorAndSummarizer()
            text = summarizer.extract_text_from_image(file_path)
            summary = summarizer.generate_summary(text) if text else None
        elif filename.lower().endswith('.pdf'):
            processor = PDFProcessor()
            text = processor.extract_text_with_ocr(file_path)
            summary = processor.summarize_text(text) if text else None
        else:
            return jsonify({'error': 'Unsupported file type'}), 400

        if not text:
            return jsonify({'error': 'Failed to extract text from the file'}), 500
        if not summary:
            return jsonify({'error': 'Failed to generate summary'}), 500

        extracted_text_file = os.path.join(app.config['OUTPUT_FOLDER'], "extracted_text.txt")
        summary_file = os.path.join(app.config['OUTPUT_FOLDER'], f"summary_{uuid.uuid4().hex}.txt")

        with open(extracted_text_file, 'w', encoding='utf-8') as f:
            f.write(text)
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)

        return jsonify({
            'extracted_text': text,
            'summary': summary,
            'download_url': f'/download/{os.path.basename(summary_file)}'

        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process_video', methods=['POST'])
def process_video():
    try:
        if 'video_file' in request.files:
            # Handle local video file
            video_file = request.files['video_file']
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(video_file.filename))
            video_file.save(video_path)
            result = video_processor.process_video(video_path, is_youtube=False)
            summary = result["summary"]

        else:
            # Handle YouTube video
            data = request.json
            video_source = data.get("video_source")
            if not video_source:
                return jsonify({"error": "YouTube video URL is required."}), 400
            result = video_processor.process_video(video_source, is_youtube=True)
            summary = result["summary"]

        # Return the summary and a download link
        summary_file = os.path.join(app.config['OUTPUT_FOLDER'], "video_summary.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)


        return jsonify({
            "summary": summary,
            "download_url": result["download_url"],
            "keywords": result["keywords"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': f'File {filename} not found'}), 404


if __name__ == '__main__':
    # Use environment variables for host/port, default to 0.0.0.0:5000 for production
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port)