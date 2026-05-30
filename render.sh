#!/bin/bash

# Start the internal Redis server
echo "Starting Redis server..."
redis-server --daemonize yes

# Start the Celery worker in the background
echo "Starting Celery worker..."
celery -A tasks.celery_app worker --loglevel=info &

# Start the FastAPI application in the foreground
# Render dynamically assigns the port via the $PORT environment variable
echo "Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
