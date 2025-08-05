import os
import uuid
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_cors import CORS
from app_factory import app, app_factory

# Enable CORS for your Chrome extension or any frontend
CORS(app, origins=["chrome-extension://ldemhkhknojajajjfomnhcpmdcfilggh"])

# Configure paths according to Render disk mount
app.config['UPLOAD_FOLDER'] = "/app/uploads/input"
app.config['OUTPUT_FOLDER'] = "/app/uploads/output"

# Ensure the folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
@app.route('/healthz', methods=['GET'])
def health():
    return 'OK', 200

@app.route('/process', methods=['POST'])
def process_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Ensure unique filename
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
            summarizer = app_factory.get_image_processor()
            text = summarizer.extract_text_from_image(file_path)
            summary = summarizer.generate_summary(text) if text else None

        elif filename.lower().endswith('.pdf'):
            processor = app_factory.get_pdf_processor()
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
        video_processor = app_factory.get_video_processor()
        if video_processor is None:
            return jsonify({"error": "Video processing is not available"}), 500

        if 'video_file' in request.files:
            video_file = request.files['video_file']
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(video_file.filename))
            video_file.save(video_path)
            result = video_processor.process_video(video_path, is_youtube=False)
        else:
            data = request.json
            video_source = data.get("video_source")
            if not video_source:
                return jsonify({"error": "YouTube video URL is required."}), 400
            result = video_processor.process_video(video_source, is_youtube=True)

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        summary = result["summary"]
        summary_file = os.path.join(app.config['OUTPUT_FOLDER'], "video_summary.txt")

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)

        return jsonify({
            "summary": summary,
            "download_url": result.get("download_url", f'/download/{os.path.basename(summary_file)}'),
            "keywords": result.get("keywords", [])
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
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port)
