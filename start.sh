#!/bin/bash
# Production startup script for Dive Bar Detective API

# Exit on error
set -e

# Default values
WORKERS=${WORKERS:-2}
PORT=${PORT:-8000}
TIMEOUT=${TIMEOUT:-120}

echo "Starting Dive Bar Detective API..."
echo "Workers: $WORKERS"
echo "Port: $PORT"
echo "Timeout: $TIMEOUT seconds"

# Start Gunicorn with Uvicorn workers
exec gunicorn src.api:app \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:$PORT \
    --timeout $TIMEOUT \
    --access-logfile - \
    --error-logfile - \
    --log-level info

