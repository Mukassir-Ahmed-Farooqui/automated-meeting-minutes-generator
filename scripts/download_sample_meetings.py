import subprocess
import os

URLS = [
    "https://www.youtube.com/watch?v=0kF3h_R0dKk", # Mock Daily Scrum
    "https://www.youtube.com/watch?v=M5yGtzE6mB0", # Standup Demo
]

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/samples"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download():
    print(f"Downloading samples to {OUTPUT_DIR}...")
    for url in URLS:
        print(f"Downloading {url}")
        subprocess.run([
            "yt-dlp",
            "-f", "best[ext=mp4]",
            "--output", f"{OUTPUT_DIR}/%(title)s.%(ext)s",
            url
        ])

if __name__ == "__main__":
    download()
