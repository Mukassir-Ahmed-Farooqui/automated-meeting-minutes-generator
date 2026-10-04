import subprocess
import os
import logging
import uuid

log = logging.getLogger("video_service")

def extract_audio(video_path: str, output_dir: str) -> str:
    """
    Extracts audio from a video file using FFmpeg and saves it as a WAV file.
    Returns the path to the extracted audio file.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    output_filename = f"{uuid.uuid4().hex}.wav"
    output_path = os.path.join(output_dir, output_filename)
    
    # Run FFmpeg to extract audio, downmix to mono, 16kHz (optimal for Whisper)
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vn",               # Disable video
        "-acodec", "pcm_s16le", # 16-bit PCM
        "-ar", "16000",      # 16 kHz sample rate
        "-ac", "1",          # Mono
        "-y",                # Overwrite output
        output_path
    ]
    
    try:
        log.info(f"Extracting audio from {video_path} to {output_path}")
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_path
    except subprocess.CalledProcessError as e:
        log.error(f"FFmpeg error: {e.stderr.decode('utf-8', errors='ignore')}")
        raise RuntimeError("Failed to extract audio from video.")
