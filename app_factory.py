from flask import Flask
from functools import lru_cache


class AppFactory:
    _instance = None
    _app = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppFactory, cls).__new__(cls)
            cls._app = Flask(__name__)
        return cls._instance

    @property
    def app(self):
        return self._app

    @lru_cache(maxsize=1)
    def get_image_processor(self):
        from image_processor import TextExtractorAndSummarizer
        return TextExtractorAndSummarizer()

    @lru_cache(maxsize=1)
    def get_pdf_processor(self):
        from pdf_processor import PDFProcessor
        return PDFProcessor()

    @lru_cache(maxsize=1)
    def get_video_processor(self):
        from video_processor import VideoProcessor
        return VideoProcessor()


app_factory = AppFactory()
app = app_factory.app
