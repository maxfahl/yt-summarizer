from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Summary:
    video_id: str
    title: str
    status: ProcessingStatus
    created_at: datetime
    summary_text: Optional[str] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None 