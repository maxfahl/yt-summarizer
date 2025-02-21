import os
from dataclasses import dataclass

@dataclass
class Config:
    openai_api_key: str
    processing_dir: str = "processing"
    summaries_file: str = "summaries.md"

def load_config() -> Config:
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    return Config(
        openai_api_key=openai_api_key,
        processing_dir=os.environ.get("PROCESSING_DIR", "processing"),
        summaries_file=os.environ.get("SUMMARIES_FILE", "summaries.md")
    ) 