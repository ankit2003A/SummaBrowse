import os
import yt_dlp
import ffmpeg
from pydub import AudioSegment
from pydub.utils import which
import uuid

AudioSegment.converter = which("ffmpeg")
AudioSegment.ffprobe   = which("ffprobe")
os.makedirs("downloads", exist_ok=True)
os.makedirs("output", exist_ok=True)

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

class YouTubeAudioProcessor:
    def __init__(self):
        self._whisper_model = None
        
    @property
    def whisper_model(self):
        if self._whisper_model is None:
            print("Loading Whisper model...")
            import whisper
            # Use the tiny model for lower memory usage
            self._whisper_model = whisper.load_model("tiny")
        return self._whisper_model

    def extract_audio_from_youtube(self, url):
        random_id = uuid.uuid4().hex
        output_audio = os.path.join("downloads", f"youtube_audio_{random_id}.mp3")
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
            'ignoreerrors': False,
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
                }
            }
        }

        # Check if cookies.txt exists in the workspace, or dynamically try browser cookies
        browsers_to_try = []
        if os.path.exists('cookies.txt'):
            browsers_to_try = [None]
        else:
            browsers_to_try = ['chrome', 'edge', 'firefox', 'opera', 'safari', None]

        last_error = None
        for browser in browsers_to_try:
            current_opts = ydl_opts.copy()
            if browser is None:
                if os.path.exists('cookies.txt'):
                    current_opts['cookiefile'] = 'cookies.txt'
            else:
                current_opts['cookiesfrombrowser'] = (browser,)

            browser_name = browser if browser else ('cookies.txt' if os.path.exists('cookies.txt') else 'none')
            print(f"Attempting download using cookies from: {browser_name}")
            try:
                with yt_dlp.YoutubeDL(current_opts) as ydl:
                    # First try with the original URL
                    try:
                        ydl.download([url])
                        if os.path.exists(output_audio) and os.path.getsize(output_audio) > 0:
                            print(f"[Success] Download successful using cookies from: {browser_name}")
                            return output_audio
                    except Exception as e:
                        print(f"First attempt failed with browser cookies '{browser_name}': {str(e)}")
                        last_error = e
                    
                    # If first attempt fails, try with a different URL format
                    try:
                        if 'youtu.be' in url:
                            video_id = url.split('/')[-1].split('?')[0]
                            new_url = f'https://www.youtube.com/watch?v={video_id}'
                        else:
                            video_id = url.split('v=')[-1].split('&')[0]
                            new_url = f'https://youtu.be/{video_id}'
                        
                        print(f"Trying alternative URL format: {new_url}")
                        ydl.download([new_url])
                        if os.path.exists(output_audio) and os.path.getsize(output_audio) > 0:
                            print(f"[Success] Alternative download successful using cookies from: {browser_name}")
                            return output_audio
                    except Exception as e:
                        print(f"Alternative URL attempt failed with browser cookies '{browser_name}': {str(e)}")
                        last_error = e
            except Exception as e:
                print(f"Could not initialize yt-dlp with browser cookies '{browser_name}': {str(e)}")
                last_error = e

        # If we still don't have a file, raise an error
        try:
            if not os.path.exists(output_audio) or os.path.getsize(output_audio) == 0:
                if last_error:
                    raise last_error
                else:
                    raise Exception("Failed to download video after multiple attempts. YouTube might be rate limiting requests. Please try again later.")
            
            return output_audio
            
        except Exception as e:
            error_msg = str(e)
            if 'HTTP Error 429' in error_msg or '429' in error_msg:
                error_msg = "YouTube is rate limiting requests. Please wait a few minutes and try again."
            elif 'Sign in to confirm' in error_msg or 'confirm you\'re not a bot' in error_msg or 'confirm you are not a bot' in error_msg:
                error_msg = (
                    "YouTube blocked this request as a bot check. To fix this:\n"
                    "1. Export your cookies from your browser (using an extension like 'Get cookies.txt LOCALLY').\n"
                    "2. Save the exported cookies as a file named 'cookies.txt' in the project directory:\n"
                    f"   Path: {os.path.abspath('cookies.txt')}\n"
                    "3. Or ensure you are logged into YouTube in your default Chrome/Edge/Firefox browser."
                )
            print(f"[Error] Error downloading from YouTube: {error_msg}")
            raise Exception(error_msg)

    def extract_audio_from_video(self, video_path):
        random_id = uuid.uuid4().hex
        output_audio = os.path.join("downloads", f"{os.path.splitext(os.path.basename(video_path))[0]}_{random_id}.mp3")
        try:
            print("[Video] Extracting audio from local video...")
            (
                ffmpeg
                .input(video_path)
                .output(output_audio, format='mp3', acodec='libmp3lame')
                .run(overwrite_output=True)
            )
            print(f"[Success] Local audio extracted: {output_audio}")
            return output_audio
        except Exception as e:
            print(f"[Error] Error extracting local audio: {e}")
            return None
    
    def convert_audio_to_wav(self, input_file, wav_file):
        audio = AudioSegment.from_file(input_file)
        audio.export(wav_file, format="wav")

    def audio_to_text(self, audio_file, transcription_path=None):
        print("[Whisper] Transcribing audio using Whisper (tiny)...")
        if not HAS_WHISPER:
            print("Warning: Whisper is not installed. Cannot transcribe audio.")
            return "Whisper is not installed. Could not transcribe audio transcript."
        try:
            result = self.whisper_model.transcribe(audio_file)
            transcription = result["text"]
            print("[Transcription] Transcription complete.")
            if transcription_path:
                with open(transcription_path, "w", encoding="utf-8") as f:
                    f.write(transcription)
            return transcription
        except Exception as e:
            print(f"Error in audio transcription: {str(e)}")
            return ""

    def save_summary_to_file(self, summary, output_file):
        from utils import clean_markdown
        clean_sum = clean_markdown(summary)
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(clean_sum + "\n")
        print(f"[File] Summary saved to {output_file}")

    def process_video(self, video_source, is_youtube=False):
        """
        Unified function to process both YouTube and local video sources.
        """
        print(f"{'YouTube' if is_youtube else 'Local'} video detected. Starting processing...")

        # Step 1: Extract audio
        try:
            if is_youtube:
                audio_file = self.extract_audio_from_youtube(video_source)
            else:
                audio_file = self.extract_audio_from_video(video_source)
        except Exception as e:
            return {
                "error": str(e),
                "summary": "",
                "download_url": ""
            }

        if not audio_file:
            return {
                "error": "Failed to extract audio from video source.",
                "summary": "",
                "download_url": ""
            }

        random_id = uuid.uuid4().hex
        wav_file_path = os.path.join("output", f"converted_audio_{random_id}.wav")
        transcription_path = os.path.join("output", f"transcription_{random_id}.txt")

        try:
            # Step 2: Convert to WAV
            self.convert_audio_to_wav(audio_file, wav_file_path)

            # Step 3: Transcribe
            transcription = self.audio_to_text(wav_file_path, transcription_path=transcription_path)

            # Step 4: Summarize
            from utils import summarize_text
            summary = summarize_text(transcription)

            summary_file = f"summary_{random_id}.txt"
            summary_path = os.path.join("output", summary_file)
            self.save_summary_to_file(summary, summary_path)

            return {
                "summary": summary,
                "download_url": f"/download/{summary_file}"
            }
        except Exception as e:
            print(f"Error processing video: {str(e)}")
            return {
                "error": f"Error processing video: {str(e)}",
                "summary": "",
                "download_url": ""
            }
        finally:
            # Clean up temporary audio and video files to prevent disk space leaks
            temp_files = [audio_file, wav_file_path, transcription_path]
            if not is_youtube and video_source and os.path.exists(video_source):
                temp_files.append(video_source)
                
            for temp_file in temp_files:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        print(f"Cleaned up temporary file: {temp_file}")
                    except Exception as clean_err:
                        print(f"Failed to remove temporary file {temp_file}: {str(clean_err)}")
