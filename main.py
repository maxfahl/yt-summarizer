#!/usr/bin/env python3
import logging
import os
import subprocess
import sys

import openai
import whisper
import yt_dlp

# Set up logging for clear step-by-step feedback
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def download_video(url, output_dir="downloads"):
    """
    Downloads a YouTube video from the given URL using yt-dlp.
    The video is saved in the specified output directory.
    Returns the path to the downloaded video file.
    """
    logging.info(f"Downloading video from URL: {url}")
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        logging.info(f"Downloaded video saved to: {filename}")
        return filename


def extract_audio(video_path, output_dir="downloads", audio_format="mp3"):
    """
    Extracts audio from the downloaded video using ffmpeg.
    The resulting audio file is saved with the given audio_format.
    Returns the path to the audio file.
    """
    logging.info(f"Extracting audio from video: {video_path}")
    base, _ = os.path.splitext(os.path.basename(video_path))
    audio_file = os.path.join(output_dir, f"{base}.{audio_format}")
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "mp3", audio_file]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Extracted audio saved to: {audio_file}")
        return audio_file
    except subprocess.CalledProcessError as e:
        logging.error("Error extracting audio using ffmpeg")
        raise e


def transcribe_audio(audio_path, model):
    """
    Transcribes the audio file using the provided local Whisper model.
    Returns the transcription text.
    """
    logging.info(f"Transcribing audio: {audio_path}")
    # Suppress FP16 warning on CPU
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")
        result = model.transcribe(audio_path)
    transcription = result.get("text", "")
    logging.info("Transcription complete")
    return transcription


def summarize_transcription(transcription, openai_api_key):
    """
    Summarizes the provided transcription text using ChatGPT.
    Returns the summary text.
    """
    logging.info("Summarizing transcription using ChatGPT")
    client = openai.OpenAI(api_key=openai_api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Changed from gpt-o3-mini which was invalid
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes transcriptions."},
                {"role": "user", "content": f"Please provide a summary for the below transcription for a short blog post, including highlights, key points and the \"meaty\" parts.\n\n---\n\n{transcription}"}
            ],
            # max_tokens=150,
            temperature=0.5,
        )
        summary = response.choices[0].message.content.strip()
        logging.info("Summary complete")
        return summary
    except Exception as e:
        logging.error("Error summarizing transcription via ChatGPT")
        raise e


def process_video(url, model, openai_api_key, output_dir="downloads"):
    """
    Full processing pipeline for a single video URL:
      1. Download the video.
      2. Extract the audio.
      3. Transcribe the audio.
      4. Summarize the transcription.
      5. Save both transcription and summary to text files.
    """
    try:
        video_path = download_video(url, output_dir)
        audio_path = extract_audio(video_path, output_dir)
        transcription = transcribe_audio(audio_path, model)
        summary = summarize_transcription(transcription, openai_api_key)
        
        # Save the transcription and summary to separate text files
        base, _ = os.path.splitext(os.path.basename(video_path))
        transcription_file = os.path.join(output_dir, f"{base}_transcription.txt")
        summary_file = os.path.join(output_dir, f"{base}_summary.txt")
        
        with open(transcription_file, "w", encoding="utf-8") as f:
            f.write(transcription)
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)
        
        logging.info(f"Transcription saved to: {transcription_file}")
        logging.info(f"Summary saved to: {summary_file}")
    except Exception as e:
        logging.error(f"Failed processing video from URL: {url}\nError: {e}")


def main():
    if len(sys.argv) < 2:
        logging.error("No YouTube URLs provided.\nUsage: python script.py <YouTube URL> [<YouTube URL> ...]")
        sys.exit(1)
    
    # Retrieve the OpenAI API key from the environment
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        logging.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        sys.exit(1)
    
    # Load the local Whisper model (using the "base" model; change as needed)
    logging.info("Loading local Whisper model (base)")
    model = whisper.load_model("base")
    
    # Process each URL provided as a command-line argument
    urls = sys.argv[1:]
    for url in urls:
        logging.info(f"Processing URL: {url}")
        process_video(url, model, openai_api_key)


if __name__ == "__main__":
    main()
