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
        # Generate a random user agent to help avoid bot detection
        import random
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': 'mp3',
            'outtmpl': output_audio,
            'quiet': False,
            'noplaylist': True,
            'ignoreerrors': True,
            'no_warnings': False,
            'extract_flat': False,
            'http_headers': {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'extractor_retries': 3,
            'retries': 5,
            'fragment_retries': 5,
            'skip_unavailable_fragments': True,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['js', 'webpage']
                }
            },
            'cookiefile': 'cookies.txt'
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # First try with the original URL
                try:
                    ydl.download([url])
                    if os.path.exists(output_audio) and os.path.getsize(output_audio) > 0:
                        return output_audio
                except Exception as e:
                    print(f"First attempt failed: {str(e)}")
                
                # If first attempt fails, try with a different URL format
                try:
                    # Try with a different URL format
                    if 'youtu.be' in url:
                        video_id = url.split('/')[-1].split('?')[0]
                        new_url = f'https://www.youtube.com/watch?v={video_id}'
                    else:
                        video_id = url.split('v=')[-1].split('&')[0]
                        new_url = f'https://youtu.be/{video_id}'
                    
                    print(f"Trying alternative URL format: {new_url}")
                    ydl.download([new_url])
                    if os.path.exists(output_audio) and os.path.getsize(output_audio) > 0:
                        return output_audio
                except Exception as e:
                    print(f"Alternative URL attempt failed: {str(e)}")
                
                # If we still don't have a file, raise an error
                if not os.path.exists(output_audio) or os.path.getsize(output_audio) == 0:
                    raise Exception("Failed to download video after multiple attempts. YouTube might be rate limiting requests. Please try again later.")
                
                return output_audio
                
        except Exception as e:
            error_msg = str(e)
            if 'HTTP Error 429' in error_msg or '429' in error_msg:
                error_msg = "YouTube is rate limiting requests. Please wait a few minutes and try again."
            elif 'Sign in to confirm you\'re not a bot' in error_msg:
                error_msg = "YouTube is blocking automated requests. Please try again later or use a different video."
            print(f"❌ Error downloading from YouTube: {error_msg}")
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
            return {
                "error": "Error extracting audio",
                "summary": "",
                "download_url": "",
                "keywords": []
            }

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



