#!/usr/bin/env python3
import os
import subprocess
import sys

import openai
import whisper
import yt_dlp
from tqdm.auto import tqdm


def download_video(url, video_dir, progress_bar=None):
    """
    Downloads a YouTube video from the given URL using yt-dlp.
    The video is saved in the specified video directory as video.{ext}.
    Returns the path to the downloaded video file.
    """
    os.makedirs(video_dir, exist_ok=True)

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

    class QuietLogger:
        def debug(self, msg): pass
        def warning(self, msg): pass
        def error(self, msg): pass

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(video_dir, 'video.%(ext)s'),
        'noplaylist': True,
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'logger': QuietLogger(),
        'noprogress': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Download the video
        info = ydl.extract_info(url, download=True)
        # Get the actual filename (with extension)
        return os.path.join(video_dir, f"video.{info['ext']}")


def extract_audio(video_path, video_dir, progress_bar=None):
    """
    Extracts audio from the downloaded video using ffmpeg.
    The resulting audio file is saved as audio.mp3.
    Returns the path to the audio file.
    """
    audio_file = os.path.join(video_dir, "audio.mp3")
    
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "mp3", audio_file]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if progress_bar:
            progress_bar.n = progress_bar.total
            progress_bar.refresh()
        return audio_file
    except subprocess.CalledProcessError as e:
        print(f"\nffmpeg command failed: {' '.join(cmd)}")
        print(f"Error output: {e.stderr.decode('utf-8')}")
        raise


def transcribe_audio(audio_path, model, progress_bar=None):
    """
    Transcribes the audio file using the provided local Whisper model.
    Returns the transcription text.
    """
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")
        result = model.transcribe(audio_path)
        if progress_bar:
            progress_bar.n = progress_bar.total
            progress_bar.refresh()
        return result.get("text", "")


def summarize_transcription(transcription, openai_api_key, progress_bar=None):
    """
    Summarizes the provided transcription text using ChatGPT.
    Returns a comprehensive summary with both highlights and detailed narrative.
    """
    client = openai.OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates comprehensive summaries of video transcriptions. Your summaries should be informative and well-structured, capturing both the key points and the deeper context."},
            {"role": "user", "content": f"""Please provide a comprehensive summary of this video transcription in the following format:

## Key Highlights
- [3-5 bullet points of the most important takeaways]

## Main Points
- [Detailed bullet points covering the major topics and arguments]

## Detailed Summary
[A few paragraphs providing a narrative summary of the content, including context, main arguments, and important details. This should be more detailed than the bullet points and help readers understand the full scope of the video.]

Here's the transcription:

---

{transcription}"""}
        ],
        temperature=0.7,  # Slightly higher temperature for more detailed generation
    )
    if progress_bar:
        progress_bar.n = progress_bar.total
        progress_bar.refresh()
    return response.choices[0].message.content.strip()


def load_whisper_model(model_name="base", progress_bar=None):
    """
    Loads the Whisper model and updates progress bar.
    """
    model = whisper.load_model(model_name)
    if progress_bar:
        progress_bar.n = progress_bar.total
        progress_bar.refresh()
    return model


def process_video(url, openai_api_key, processing_dir="processing"):
    """
    Process a video through multiple steps: download, audio extraction, transcription, and summarization.
    Each step is shown with its own progress bar. Will resume from the last completed step if files exist.
    """
    from tqdm.auto import tqdm

    # Ensure processing directory exists
    os.makedirs(processing_dir, exist_ok=True)

    # First, get the video ID to create its directory
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_id = info['id']
            video_title = info['title']
    except Exception as e:
        print(f"\nError getting video info: {str(e)}")
        raise

    if not video_id:
        raise ValueError("Could not get video ID from URL")

    # Create video-specific directory
    video_dir = os.path.join(processing_dir, video_id)
    os.makedirs(video_dir, exist_ok=True)

    # Define the steps and their descriptions
    steps = [
        ("Loading transcription model", load_whisper_model, ["base"]),
        ("Downloading", download_video, [url, video_dir]),
        ("Extracting audio", extract_audio, [None, video_dir]),
        ("Transcribing", transcribe_audio, [None, None]),  # Model will be set after loading
        ("Summarizing content", summarize_transcription, [None, openai_api_key])
    ]
    
    progress_bars = []
    try:
        # Create all progress bars at start
        for i, (desc, _, _) in enumerate(steps):
            total = 100  # Use percentage for all bars
            if desc == "Downloading":
                # Download will update its total based on file size
                total = 1
            
            pbar = tqdm(
                total=total,
                desc=desc,
                leave=True,
                position=i,
                bar_format='{desc} {bar}',
                unit='%' if total == 100 else 'B',
                unit_scale=True if desc == "Downloading" else False
            )
            progress_bars.append(pbar)

        # Check for existing files to determine where to resume
        model = None
        video_path = None
        audio_path = None
        transcription = None

        # Define expected file paths
        for ext in ['webm', 'mp4', 'mkv']:  # Common video formats
            temp_path = os.path.join(video_dir, f"video.{ext}")
            if os.path.exists(temp_path):
                video_path = temp_path
                break

        audio_file = os.path.join(video_dir, "audio.mp3")
        transcription_file = os.path.join(video_dir, "transcription.txt")

        # Load the model first
        model = load_whisper_model("base", progress_bars[0])
        if not model:
            raise ValueError("Failed to load Whisper model")

        # Check for existing transcription
        if os.path.exists(transcription_file):
            with open(transcription_file, 'r', encoding='utf-8') as f:
                transcription = f.read()
            # Complete progress bars up to transcription
            for i in range(4):  # Load model, download, extract, transcribe
                progress_bars[i].n = progress_bars[i].total
                progress_bars[i].refresh()

        # Check for existing audio
        if os.path.exists(audio_file):
            audio_path = audio_file
            if not transcription:  # Only update if not already updated by transcription check
                # Complete progress bars up to audio extraction
                for i in range(3):  # Load model, download, extract
                    progress_bars[i].n = progress_bars[i].total
                    progress_bars[i].refresh()

        # Check video file
        if video_path and os.path.exists(video_path):
            if not audio_path and not transcription:  # Only update if not already updated
                # Complete progress bars up to download
                for i in range(2):  # Load model, download
                    progress_bars[i].n = progress_bars[i].total
                    progress_bars[i].refresh()

        # Execute each remaining step
        for i, (desc, func, args) in enumerate(steps):
            # Skip steps that have already been completed
            if i == 0:  # Skip model loading as it's already done
                continue
            if i == 1 and video_path and os.path.exists(video_path):
                continue
            if i == 2 and audio_path and os.path.exists(audio_path):
                continue
            if i == 3 and transcription:
                continue

            # Update arguments with results from previous steps
            if i == 2:  # extract_audio
                args[0] = video_path
            elif i == 3:  # transcribe_audio
                args[0] = audio_path
                args[1] = model
            elif i == 4:  # summarize_transcription
                args[0] = transcription

            # Add progress bar to function arguments
            args.append(progress_bars[i])

            # Execute step
            result = func(*args)
            
            # Store results needed for next steps
            if i == 1:
                video_path = result
            elif i == 2:
                audio_path = result
            elif i == 3:
                transcription = result

            # Ensure progress bar is complete
            progress_bars[i].n = progress_bars[i].total
            progress_bars[i].refresh()

        # Save the transcription
        if transcription:
            with open(transcription_file, "w", encoding="utf-8") as f:
                f.write(transcription)

        # Clean up files based on environment settings
        keep_videos = os.environ.get("KEEP_VIDEOS", "false").lower() == "true"
        keep_audio = os.environ.get("KEEP_AUDIO", "false").lower() == "true"
        keep_transcripts = os.environ.get("KEEP_TRANSCRIPTS", "false").lower() == "true"

        if not keep_videos and video_path and os.path.exists(video_path):
            os.remove(video_path)
        if not keep_audio and audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if not keep_transcripts and os.path.exists(transcription_file):
            os.remove(transcription_file)

        # If nothing is being kept, try to remove the video directory
        if not any([keep_videos, keep_audio, keep_transcripts]):
            try:
                os.rmdir(video_dir)
            except OSError:
                pass  # Directory might not be empty if there are other files

            # Try to remove the processing directory if it's empty
            try:
                os.rmdir(processing_dir)
            except OSError:
                pass  # Directory might not be empty if there are other videos

        return {"id": video_id, "title": video_title, "summary": result}

    except Exception as e:
        # If an error occurs, mark the current and remaining steps as failed
        current_step = next((i for i, bar in enumerate(progress_bars) if bar.n < bar.total), len(progress_bars))
        for i in range(current_step, len(progress_bars)):
            progress_bars[i].set_description(f"Failed: {steps[i][0]}")
            progress_bars[i].refresh()
        raise  # Re-raise the exception to be caught by the main function
    finally:
        # Close all progress bars
        for pbar in progress_bars:
            pbar.close()


def append_summary_to_markdown(video_id: str, title: str, summary: str):
    """
    Prepends a new summary to the summaries.md file.
    """
    from datetime import datetime
    
    # Create the markdown content for this summary
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_content = f"# {title} (ID: {video_id})\n*Generated on {timestamp}*\n\n{summary}\n\n---\n\n"
    
    # Read existing content if file exists
    existing_content = ""
    if os.path.exists("summaries.md"):
        with open("summaries.md", "r", encoding="utf-8") as f:
            existing_content = f.read()
    
    # Write new content followed by existing content
    with open("summaries.md", "w", encoding="utf-8") as f:
        f.write(new_content + existing_content)


def main():
    if len(sys.argv) < 2:
        print("No YouTube URLs provided.\nUsage: python script.py <YouTube URL> [<YouTube URL> ...]")
        sys.exit(1)

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        sys.exit(1)

    urls = sys.argv[1:]
    summaries = []
    processing_dir = "processing"
    os.makedirs(processing_dir, exist_ok=True)

    # Show overall progress for multiple videos
    total_videos = len(urls)
    if total_videos > 1:
        print(f"\nProcessing {total_videos} videos:")
    
    try:
        for i, url in enumerate(urls, 1):
            if total_videos > 1:
                print(f"\nVideo {i} of {total_videos}:")
            try:
                result = process_video(url, openai_api_key, processing_dir)
                if result:
                    append_summary_to_markdown(result["id"], result["title"], result["summary"])
                    summaries.append(result)
            except Exception as e:
                print(f"\nError processing video {url}: {str(e)}")
                continue
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting gracefully.")
        sys.exit(0)

    if summaries:
        if total_videos > 1:
            print(f"\nSuccessfully processed {len(summaries)} of {total_videos} videos.")
        print("\nSummaries have been added to summaries.md")
    else:
        print("\nNo videos processed successfully.")


if __name__ == "__main__":
    main()
