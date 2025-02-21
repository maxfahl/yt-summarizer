from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional
from ..models.summary import Summary, ProcessingStatus

class VideoRequest(BaseModel):
    url: HttpUrl

class SummaryResponse(BaseModel):
    video_id: str
    title: Optional[str] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    summary_text: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_summary(cls, summary: Summary):
        return cls(
            video_id=summary.video_id,
            title=summary.title,
            status=summary.status.value,
            created_at=summary.created_at,
            completed_at=summary.completed_at,
            summary_text=summary.summary_text,
            error=summary.error
        ) 