import openai
from typing import Optional
from ..models.summary import Summary, ProcessingStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SummaryGenerator:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    def generate_summary(self, transcription: str) -> str:
        """Generates a summary from the transcription using OpenAI's API"""
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates comprehensive summaries of video transcriptions. Your summaries should be informative and well-structured, capturing both the key points and the deeper context."},
                {"role": "user", "content": f"""Please provide a comprehensive summary of this video transcription in the following format:

## Key Highlights
- [3-5 bullet points of the most important takeaways]

## Main Points
- [Detailed bullet points covering the major topics and arguments]

## Detailed Summary
[A few paragraphs providing a narrative summary of the content]

Transcription:
{transcription}"""}
            ],
            temperature=0.7,
        )
        
        return response.choices[0].message.content.strip() 