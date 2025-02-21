#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source conda.sh to enable conda command
source ~/miniconda3/etc/profile.d/conda.sh

# Activate the conda environment (replace 'base' with your environment name if different)
conda activate base

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if any URLs were provided
if [ $# -eq 0 ]; then
    echo "No YouTube URLs provided."
    echo "Usage: $0 <YouTube URL> [<YouTube URL> ...]"
    exit 1
fi

# Run the Python script with all provided URLs
python main.py "$@"

# Deactivate the conda environment
conda deactivate 