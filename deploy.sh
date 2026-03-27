#!/bin/bash

echo "🚀 Deploying AI Trading Dashboard with Auto-Broadcaster"
echo "========================================================"

# Install dependencies
pip install -r requirements.txt

# Install ffmpeg for video processing
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get update
    sudo apt-get install -y ffmpeg
elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew install ffmpeg
fi

# Set up environment variables
echo "Setting up environment..."
cp .env.example .env

# Start the Streamlit app with auto-reload
echo "Starting dashboard with auto-broadcaster..."
streamlit run famous.py --server.port=8501 --server.address=0.0.0.0

echo "✅ Dashboard is running at http://localhost:8501"
echo "🤖 Auto-broadcaster is active and posting to all channels"
