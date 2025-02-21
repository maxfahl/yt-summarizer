#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source conda.sh to enable conda command
source ~/miniconda3/etc/profile.d/conda.sh

# Activate the conda environment
conda activate yt-summarizer

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if uvicorn is installed, if not install it
if ! command -v uvicorn &> /dev/null; then
    echo "Installing uvicorn..."
    pip install uvicorn fastapi
fi

# Set default host and port if not provided in environment
export API_HOST=${API_HOST:-"0.0.0.0"}
export API_PORT=${API_PORT:-8000}

# Start the FastAPI server with hot reload enabled
echo "Starting Video Summarizer API server on ${API_HOST}:${API_PORT}..."
uvicorn src.main:app \
    --host ${API_HOST} \
    --port ${API_PORT} \
    --reload \
    --reload-dir src \
    --log-level debug

# The server will keep running until interrupted with Ctrl+C
# When interrupted, deactivate the conda environment
trap "conda deactivate" EXIT