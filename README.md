# YouTube Video Summarizer

A FastAPI-based service that automatically generates summaries of YouTube videos using OpenAI's language models.

## Features

- Download and process YouTube videos
- Extract audio for transcription
- Generate comprehensive summaries using AI
- Store summaries in markdown format
- RESTful API interface

## Prerequisites

- Python 3.12+
- Miniconda/Anaconda
- FFmpeg
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd yt-summarizer
```

2. Set up Conda environment:
```bash
conda create -n yt-summarizer python=3.12
conda activate yt-summarizer
```

3. Install dependencies:
```bash
conda install ffmpeg
pip install -r requirements.txt
```

4. Configure environment:
Create a `.env` file in the project root with:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Start the server:
```bash
./run_summarizer.sh
```
The server will start on `http://0.0.0.0:8000` by default.

2. Submit a video for summarization:
```bash
curl -X POST "http://localhost:8000/videos/" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"}'
```

3. The summary will be generated asynchronously and saved to `summaries.md` in the project root.

## API Endpoints

### POST /videos/
Submit a video for summarization

**Request Body:**
```json
{
    "url": "string"  // YouTube video URL
}
```

**Response:**
```json
{
    "video_id": "string",
    "title": "string",
    "status": "string",
    "created_at": "datetime",
    "completed_at": "datetime",
    "summary_text": "string",
    "error": "string"
}
```

## Output Format

Summaries are stored in `summaries.md` with the following structure:
```markdown
# Video Title (ID: VIDEO_ID)
*Generated on DATE*

## Key Highlights
- Important points from the video

## Main Points
- Detailed breakdown of main topics

## Detailed Summary
Comprehensive summary of the video content
```

## Environment Variables

- `API_HOST`: Host to bind the server (default: "0.0.0.0")
- `API_PORT`: Port to run the server on (default: 8000)
- `OPENAI_API_KEY`: Your OpenAI API key

## Troubleshooting

1. If you see `CondaError: Run 'conda init' before 'conda activate'`:
   ```bash
   conda init zsh  # or bash, depending on your shell
   ```
   Then restart your terminal.

2. If FFmpeg is missing:
   ```bash
   conda install ffmpeg
   ```

## License

[Add your license information here] 