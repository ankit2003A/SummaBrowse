import os
from dotenv import load_dotenv
load_dotenv()

from flask import render_template, request, send_from_directory, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from app_factory import app_factory, app

CORS(app)

# Config
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
OUTPUT_FOLDER = os.path.join(os.getcwd(), 'output')
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, DOWNLOAD_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Optional: Health check route for Render
@app.route('/healthz')
def healthz():
    return "OK", 200

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)

    _, ext = os.path.splitext(filename.lower())

    try:
        if ext == '.pdf':
            pdf_processor = app_factory.get_pdf_processor()
            extracted_text = pdf_processor.extract_text_with_ocr(input_path)
            if not extracted_text:
                return jsonify({"error": "Could not extract text from PDF file"}), 500
            summary = pdf_processor.summarize_text(extracted_text)
        else:
            # Assume image
            image_processor = app_factory.get_image_processor()
            extracted_text = image_processor.extract_text_from_image(input_path)
            if not extracted_text:
                return jsonify({"error": "Could not extract text from image file"}), 500
            summary = image_processor.generate_summary(extracted_text)

        # Save summary to output folder
        output_filename = os.path.splitext(filename)[0] + "_summary.txt"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        from utils import clean_markdown
        clean_summary = clean_markdown(summary)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(clean_summary)

        return jsonify({
            "extracted_text": extracted_text,
            "summary": summary,
            "download_url": f"/download/{output_filename}"
        })
    except Exception as e:
        print("Error processing file:", str(e))
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

@app.route('/process_video', methods=['POST'])
def process_video():
    video_processor = app_factory.get_video_processor()

    try:
        # Check if JSON request (YouTube URL)
        if request.is_json:
            data = request.get_json()
            video_source = data.get('video_source')
            is_youtube = data.get('is_youtube', False)
            if not video_source:
                return jsonify({"error": "No video source provided"}), 400

            result = video_processor.process_video(video_source, is_youtube=is_youtube)
            return jsonify(result)
        # Check if multipart form request (local video upload)
        else:
            if 'video_file' not in request.files:
                return jsonify({"error": "No video file provided"}), 400

            file = request.files['video_file']
            if file.filename == '':
                return jsonify({"error": "No selected file"}), 400

            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_path)

            result = video_processor.process_video(input_path, is_youtube=False)
            return jsonify(result)
    except Exception as e:
        print("Error processing video:", str(e))
        return jsonify({"error": f"Error processing video: {str(e)}"}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

def main():
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
