#!/bin/bash
# Production start script for CascadingTrust API
# Uses gunicorn with uvicorn workers for better performance and stability

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check for required environment variables
if [ -z "$JWT_SECRET_KEY" ]; then
    echo "ERROR: JWT_SECRET_KEY environment variable is not set!"
    echo "Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(64))\""
    exit 1
fi

# Set production mode
export PRODUCTION=true

# Number of workers (2-4 x CPU cores is recommended)
WORKERS=${WORKERS:-4}

echo "Starting CascadingTrust API in PRODUCTION mode..."
echo "Workers: $WORKERS"

# Use gunicorn with uvicorn workers
# - Proper process management
# - Graceful restarts
# - Better performance under load
exec gunicorn app:app \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance

