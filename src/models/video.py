from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Video:
    id: str
    url: str
    title: Optional[str] = None
    created_at: datetime = datetime.now()
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    transcription_path: Optional[str] = None 