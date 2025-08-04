from flask import Flask
from functools import lru_cache

class AppFactory:
    _instance = None
    _app = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppFactory, cls).__new__(cls)
            cls._app = Flask(__name__)
            # Initialize with minimal configuration
            cls._app.config.update(
                UPLOAD_FOLDER='uploads',
                OUTPUT_FOLDER='output',
                MAX_CONTENT_LENGTH=100 * 1024 * 1024  # 100MB max file size
            )
        return cls._instance
    
    @property
    def app(self):
        return self._app
    
    @lru_cache(maxsize=1)
    def get_image_processor(self):
        # Lazy load image processor
        from image_processor import TextExtractorAndSummarizer
        return TextExtractorAndSummarizer()
    
    @lru_cache(maxsize=1)
    def get_pdf_processor(self):
        # Lazy load PDF processor
        from pdf_processor import PDFProcessor
        return PDFProcessor()
    
    @lru_cache(maxsize=1)
    def get_video_processor(self):
        # Lazy load video processor only when needed
        from video_processor import YouTubeAudioProcessor
        return YouTubeAudioProcessor()

# Create a single instance
app_factory = AppFactory()
app = app_factory.app
