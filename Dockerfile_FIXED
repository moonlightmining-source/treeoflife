# Tree of Life AI Backend - Dockerfile
# Fixed version for main.py in root directory

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (main.py is in root directory)
COPY main.py .

# Expose port (Render will set this via $PORT environment variable)
EXPOSE 8000

# Start command - Run from main.py in root, not app/main.py
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
