#!/usr/bin/env python3
import os
import subprocess
import sys

import openai
import whisper
import yt_dlp
from tqdm.auto import tqdm


def clean_filename(s):
    """Clean filename by removing spaces before punctuation and normalizing Unicode characters"""
    import re
    import unicodedata
    # Normalize Unicode characters (NFKC handles full-width to half-width conversion)
    s = unicodedata.normalize('NFKC', s)
    # Remove spaces before punctuation
    s = re.sub(r'\s+([?.!,)])', r'\1', s)
    return s


def download_video(url, output_dir="downloads", progress_bar=None):
    """
    Downloads a YouTube video from the given URL using yt-dlp.
    The video is saved in the specified output directory using the video ID.
    Returns the path to the downloaded video file.
    """
    os.makedirs(output_dir, exist_ok=True)

    def progress_hook(d):
        if d['status'] == 'downloading':
            if progress_bar is not None:
                current = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    progress_bar.total = total
                    progress_bar.n = current
                    progress_bar.refresh()
        elif d['status'] == 'finished' and progress_bar is not None:
            progress_bar.n = progress_bar.total
            progress_bar.refresh()

    class QuietLogger:
        def debug(self, msg): pass
        def warning(self, msg): pass
        def error(self, msg): pass

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'noplaylist': True,
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'logger': QuietLogger(),
        'noprogress': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info and get video ID
            info = ydl.extract_info(url, download=False)
            video_id = info['id']
            # Download the video
            ydl.process_video_result(info, download=True)
            # Get the actual filename (with extension)
            filename = os.path.join(output_dir, f"{video_id}.{info['ext']}")
            return filename
    finally:
        if progress_bar is not None:
            progress_bar.n = progress_bar.total
            progress_bar.refresh()


def extract_audio(video_path, output_dir="downloads", progress_bar=None):
    """
    Extracts audio from the downloaded video using ffmpeg.
    The resulting audio file is saved with the given audio_format.
    Returns the path to the audio file.
    """
    base, _ = os.path.splitext(os.path.basename(video_path))
    # Clean the base name to ensure consistency
    base = clean_filename(base)
    audio_file = os.path.join(output_dir, f"{base}.mp3")
    
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
        raise e


def transcribe_audio(audio_path, model, progress_bar=None):
    """
    Transcribes the audio file using the provided local Whisper model.
    Returns the transcription text.
    """
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")
        
        try:
            # Transcribe without progress callback (not supported by Whisper)
            result = model.transcribe(audio_path)
            if progress_bar:
                progress_bar.n = progress_bar.total
                progress_bar.refresh()
            return result.get("text", "")
        finally:
            pass  # Don't close the progress bar, it's managed by the caller


def summarize_transcription(transcription, openai_api_key):
    """
    Summarizes the provided transcription text using ChatGPT.
    Returns the summary text.
    """
    client = openai.OpenAI(api_key=openai_api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes transcriptions."},
                {"role": "user", "content": f"Please provide a summary for the below transcription for a short blog post, including highlights, key points and the \"meaty\" parts.\n\n---\n\n{transcription}"}
            ],
            temperature=0.5,
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        raise e


def load_whisper_model(model_name="base", progress_bar=None):
    """
    Loads the Whisper model and updates progress bar.
    """
    try:
        model = whisper.load_model(model_name)
        if progress_bar:
            progress_bar.n = progress_bar.total
            progress_bar.refresh()
        return model
    except Exception as e:
        raise e


def normalize_filename(filename):
    """
    Normalizes a filename by:
    1. Converting full-width characters to half-width
    2. Normalizing Unicode characters
    3. Converting to lowercase for case-insensitive comparison
    """
    import unicodedata
    # Normalize Unicode characters (NFKC handles full-width to half-width conversion)
    normalized = unicodedata.normalize('NFKC', filename)
    # Convert to lowercase for case-insensitive comparison
    return normalized.lower()


def process_video(url, openai_api_key, output_dir="downloads"):
    """
    Process a video through multiple steps: download, audio extraction, transcription, and summarization.
    Each step is shown with its own progress bar. Will resume from the last completed step if files exist.
    """
    from tqdm.auto import tqdm

    # Define the steps and their descriptions
    steps = [
        ("Loading transcription model", load_whisper_model, ["base"]),
        ("Downloading", download_video, [url, output_dir]),
        ("Extracting audio", extract_audio, [None, output_dir]),
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
        summary = None
        video_id = None
        video_title = None

        # First, try to get the video ID and expected filenames
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                video_id = info['id']
                video_title = info['title']
                # Look for existing video file
                for file in os.listdir(output_dir):
                    base, ext = os.path.splitext(file)
                    if base == video_id:
                        video_path = os.path.join(output_dir, file)
                        break
        except Exception:
            pass

        if video_id:
            # Check files in reverse order (from final step backwards)
            # Find summary file
            summary_file = os.path.join(output_dir, f"{video_id}_summary.txt")
            if os.path.exists(summary_file):
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary = f.read()
                # Complete all progress bars as everything is done
                for i in range(len(progress_bars)):
                    progress_bars[i].n = progress_bars[i].total
                    progress_bars[i].refresh()
                return {"id": video_id, "title": video_title, "summary": summary}

            # Find transcription file
            transcription_file = os.path.join(output_dir, f"{video_id}_transcription.txt")
            if os.path.exists(transcription_file):
                with open(transcription_file, 'r', encoding='utf-8') as f:
                    transcription = f.read()
                # Complete progress bars up to transcription
                for i in range(4):  # Load model, download, extract, transcribe
                    progress_bars[i].n = progress_bars[i].total
                    progress_bars[i].refresh()

            # Find audio file
            audio_path = os.path.join(output_dir, f"{video_id}.mp3")
            if os.path.exists(audio_path):
                if not transcription:  # Only update if not already updated by transcription check
                    # Complete progress bars up to audio extraction
                    for i in range(3):  # Load model, download, extract
                        progress_bars[i].n = progress_bars[i].total
                        progress_bars[i].refresh()

            # Check video file
            if os.path.exists(video_path):
                if not audio_path and not transcription:  # Only update if not already updated
                    # Complete progress bars up to download
                    for i in range(2):  # Load model, download
                        progress_bars[i].n = progress_bars[i].total
                        progress_bars[i].refresh()
            else:
                video_path = None  # Reset if file doesn't exist

        # Load the model first
        model = load_whisper_model("base", progress_bars[0])

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
            if i == 4 and summary:
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
                # Update video_id from the actual downloaded file
                video_id = os.path.splitext(os.path.basename(video_path))[0]
            elif i == 2:
                audio_path = result
            elif i == 3:
                transcription = result

            # Ensure progress bar is complete
            progress_bars[i].n = progress_bars[i].total
            progress_bars[i].refresh()

        # Save the transcription and summary to separate text files
        transcription_file = os.path.join(output_dir, f"{video_id}_transcription.txt")
        summary_file = os.path.join(output_dir, f"{video_id}_summary.txt")

        with open(transcription_file, "w", encoding="utf-8") as f:
            f.write(transcription)
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(result)  # result here is the summary from the last step

        # Clean up files based on environment settings
        keep_videos = os.environ.get("KEEP_VIDEOS", "false").lower() == "true"
        keep_audio = os.environ.get("KEEP_AUDIO", "false").lower() == "true"
        keep_transcripts = os.environ.get("KEEP_TRANSCRIPTS", "false").lower() == "true"

        if not keep_videos and video_path and os.path.exists(video_path):
            os.remove(video_path)
        if not keep_audio and audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if not keep_transcripts:
            if os.path.exists(transcription_file):
                os.remove(transcription_file)

        # If nothing is being kept, try to remove the downloads directory
        if not any([keep_videos, keep_audio, keep_transcripts]):
            try:
                # Only remove if directory is empty
                os.rmdir(output_dir)
            except OSError:
                # Directory might not be empty if there are other files, that's okay
                pass

        return {"id": video_id, "title": video_title, "summary": result}

    except Exception as e:
        # If an error occurs, mark the current and remaining steps as failed
        current_step = next((i for i, bar in enumerate(progress_bars) if bar.n < bar.total), len(progress_bars))
        for i in range(current_step, len(progress_bars)):
            progress_bars[i].set_description(f"Failed: {steps[i][0]}")
            progress_bars[i].refresh()
        print(f"\nError processing video {url}: {str(e)}")
        return None
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
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)

    # Show overall progress for multiple videos
    total_videos = len(urls)
    if total_videos > 1:
        print(f"\nProcessing {total_videos} videos:")
    
    try:
        for i, url in enumerate(urls, 1):
            if total_videos > 1:
                print(f"\nVideo {i} of {total_videos}:")
            result = process_video(url, openai_api_key, output_dir)
            if result:
                append_summary_to_markdown(result["id"], result["title"], result["summary"])
                summaries.append(result)
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
