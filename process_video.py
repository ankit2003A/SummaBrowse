import os
import yt_dlp
import ffmpeg
import whisper
from pydub import AudioSegment
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from pydub.utils import which
import uuid

AudioSegment.converter = which("ffmpeg")
AudioSegment.ffprobe   = which("ffprobe")
os.makedirs("downloads", exist_ok=True)
os.makedirs("output", exist_ok=True)

class YouTubeAudioProcessor:
    def __init__(self):
        self.summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

    def extract_audio_from_youtube(self, url):
        output_audio = "downloads/youtube_audio.mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': 'mp3',
            'outtmpl': output_audio,
            'quiet': False
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            print(f"✅ YouTube audio saved as {output_audio}")
            return output_audio
        except Exception as e:
            print(f"❌ Error downloading from YouTube: {e}")
            return None

    def extract_audio_from_video(self, video_path):
        output_audio = os.path.join("downloads", os.path.splitext(os.path.basename(video_path))[0] + ".mp3")
        try:
            print("⏳ Extracting audio from local video...")
            (
                ffmpeg
                .input(video_path)
                .output(output_audio, format='mp3', acodec='libmp3lame')
                .run(overwrite_output=True)
            )
            print(f"✅ Local audio extracted: {output_audio}")
            return output_audio
        except Exception as e:
            print(f"❌ Error extracting local audio: {e}")
            return None
    
    def convert_audio_to_wav(self, input_file, wav_file):
        audio = AudioSegment.from_file(input_file)
        audio.export(wav_file, format="wav")

    def audio_to_text(self, audio_file):
        print("🔊 Transcribing audio using Whisper (tiny)...")
        model = whisper.load_model("tiny")  # Use tiny model for speed
        result = model.transcribe(audio_file)
        transcription = result["text"]
        print("📝 Transcription complete.")
        with open("output/transcription.txt", "w", encoding="utf-8") as f:
            f.write(transcription)
        return transcription

    def summarize_text(self, text):
        max_chunk = 512  # Larger chunk for efficiency
        chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
        summarized_chunks = []
        for chunk in chunks:
            summary = self.summarizer(chunk, max_length=200, min_length=30, do_sample=False)
            summarized_chunks.append(summary[0]['summary_text'])
        return "\n".join(summarized_chunks)

    def extract_keywords(self, text, num_keywords=10):
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.sum(axis=0).A1
        keywords = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
        return [keyword for keyword, _ in keywords[:num_keywords]]

    def save_summary_to_file(self, summary, keywords, output_file):
        with open(output_file, "w", encoding="utf-8") as file:
            file.write("📄 Document Summary\n")
            file.write("=" * 50 + "\n\n")
            file.write(summary + "\n\n")
            file.write("✨ Key Topics & Keywords ✨\n")
            file.write("-" * 50 + "\n")
            file.write(", ".join(keywords) + "\n")
        print(f"📁 Summary saved to {output_file}")

    def process_video(self, video_source, is_youtube=False):
        """
        Unified function to process both YouTube and local video sources.
        """
        print(f"{'🌐 YouTube' if is_youtube else '💻 Local'} video detected. Starting processing...")

        # Step 1: Extract audio
        if is_youtube:
            audio_file = self.extract_audio_from_youtube(video_source)
        else:
            audio_file = self.extract_audio_from_video(video_source)

        if not audio_file:
            return "❌ Error extracting audio."

        # Step 2: Convert to WAV
        wav_file_path = "output/converted_audio.wav"
        self.convert_audio_to_wav(audio_file, wav_file_path)

        # Step 3: Transcribe
        transcription = self.audio_to_text(wav_file_path)

        # Step 4: Summarize
        summary = self.summarize_text(transcription)

        # Step 5: Extract keywords
        keywords = self.extract_keywords(transcription)

        summary_file = f"summary_{uuid.uuid4().hex}.txt"
        summary_path = os.path.join("output", summary_file)
        self.save_summary_to_file(summary, keywords, summary_path)

        return {
            "summary": summary,
            "download_url": f"/download/{summary_file}",
            "keywords": keywords           
}



