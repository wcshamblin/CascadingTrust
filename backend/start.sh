#!/bin/bash
# Development start script - uses hot reload for development
# For production, use start-prod.sh or the systemd service

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start uvicorn with hot reload for development
echo "Starting CascadingTrust API in DEVELOPMENT mode..."
echo "Using hot-reload. For production, use start-prod.sh"
python3 -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
