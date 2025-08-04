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
        # Don't load the model until it's actually needed
        self._summarizer = None
        self._whisper_model = None
        
    @property
    def summarizer(self):
        if self._summarizer is None:
            print("Loading summarization model...")
            from transformers import pipeline
            # Use a smaller model for summarization
            self._summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        return self._summarizer
        
    @property
    def whisper_model(self):
        if self._whisper_model is None:
            print("Loading Whisper model...")
            import whisper
            # Use the tiny model for lower memory usage
            self._whisper_model = whisper.load_model("tiny")
        return self._whisper_model

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
        try:
            result = self.whisper_model.transcribe(audio_file)
            transcription = result["text"]
            print("📝 Transcription complete.")
            with open("output/transcription.txt", "w", encoding="utf-8") as f:
                f.write(transcription)
            return transcription
        except Exception as e:
            print(f"Error in audio transcription: {str(e)}")
            return ""

    def summarize_text(self, text):
        if not text.strip():
            return "No text to summarize"
            
        try:
            max_chunk = 1000  # Larger chunk to reduce API calls
            chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
            print(f"Processing {len(chunks)} chunks for summarization...")
            
            # Process chunks in batches to save memory
            batch_size = 2
            summarized_chunks = []
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i+batch_size]
                try:
                    # Process batch
                    summaries = self.summarizer(
                        batch,
                        max_length=150,  # Shorter summaries
                        min_length=30,
                        do_sample=False,
                        truncation=True
                    )
                    summarized_chunks.extend([s['summary_text'] for s in summaries])
                    # Clear memory after each batch
                    import torch
                    torch.cuda.empty_cache() if torch.cuda.is_available() else None
                except Exception as e:
                    print(f"Error in batch {i//batch_size + 1}: {str(e)}")
                    # Fallback: take first few sentences if summarization fails
                    for chunk in batch:
                        sentences = chunk.split('. ')
                        summarized_chunks.append('. '.join(sentences[:2]) + '.')
            
            return " ".join(summarized_chunks)
            
        except Exception as e:
            print(f"Error in summarization: {str(e)}")
            # Fallback: return first 200 characters if everything fails
            return text[:200] + "..." if len(text) > 200 else text

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



