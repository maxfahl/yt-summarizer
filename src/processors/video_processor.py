import os
import subprocess
from typing import Optional
import yt_dlp
import whisper
from tqdm.auto import tqdm

from ..models.video import Video
from ..utils.logger import get_logger

logger = get_logger(__name__)

class VideoProcessor:
    def __init__(self, processing_dir: str = "processing"):
        self.processing_dir = processing_dir
        self.model = None
        
    def _ensure_dirs(self):
        os.makedirs(self.processing_dir, exist_ok=True)
    
    def _get_video_dir(self, video_id: str) -> str:
        video_dir = os.path.join(self.processing_dir, video_id)
        os.makedirs(video_dir, exist_ok=True)
        return video_dir

    def download_video(self, url: str, progress_bar=None) -> Video:
        """Downloads a YouTube video and returns a Video object"""
        self._ensure_dirs()
        
        # Extract video info first
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_id = info['id']
            video_title = info['title']

        video_dir = self._get_video_dir(video_id)
        
        def progress_hook(d):
            if progress_bar is not None:
                if d['status'] == 'downloading':
                    current = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    if total > 0:
                        progress_bar.total = total
                        progress_bar.n = current
                        progress_bar.refresh()
                elif d['status'] == 'finished':
                    progress_bar.n = progress_bar.total
                    progress_bar.refresh()

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(video_dir, 'video.%(ext)s'),
            'noplaylist': True,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = os.path.join(video_dir, f"video.{info['ext']}")
            
            return Video(
                id=video_id,
                url=url,
                title=video_title,
                video_path=video_path
            )

    # ... Rest of the methods (extract_audio, transcribe_audio, etc.) will follow similar pattern 