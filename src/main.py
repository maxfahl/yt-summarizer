import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from typing import List

from .api.schemas import VideoRequest, SummaryResponse
from .processors.video_processor import VideoProcessor
from .processors.summary_generator import SummaryGenerator
from .processors.markdown_formatter import MarkdownFormatter
from .models.summary import Summary, ProcessingStatus
from .utils.config import load_config

app = FastAPI(
    title="Video Summarizer API",
    description="API for processing and summarizing YouTube videos",
    version="1.0.0"
)

# Initialize processors
config = load_config()
video_processor = VideoProcessor(processing_dir=config.processing_dir)
summary_generator = SummaryGenerator(api_key=config.openai_api_key)
markdown_formatter = MarkdownFormatter(output_file=config.summaries_file)

@app.post("/videos/", response_model=SummaryResponse)
async def create_video_summary(video_request: VideoRequest, background_tasks: BackgroundTasks):
    try:
        # Download and process video
        video = video_processor.download_video(video_request.url)
        
        # Create initial summary object
        summary = Summary(
            video_id=video.id,
            title=video.title,
            status=ProcessingStatus.PROCESSING,
            created_at=video.created_at
        )
        
        # Add processing task to background
        background_tasks.add_task(process_video, video, summary)
        
        return SummaryResponse.from_summary(summary)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def process_video(video, summary):
    try:
        # Extract audio
        audio_path = video_processor.extract_audio(video)
        
        # Transcribe audio
        transcription = video_processor.transcribe_audio(audio_path)
        
        # Generate summary
        summary_text = summary_generator.generate_summary(transcription)
        
        # Update summary
        summary.summary_text = summary_text
        summary.status = ProcessingStatus.COMPLETED
        
        # Add to markdown file
        markdown_formatter.append_summary(summary)
        
    except Exception as e:
        summary.status = ProcessingStatus.FAILED
        summary.error = str(e) 