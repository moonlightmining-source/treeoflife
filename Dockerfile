# Tree of Life AI Backend - Dockerfile
# For structure with app/ directory containing main.py

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

# Copy the entire app directory (contains main.py and all modules)
COPY app/ ./app/

# Copy alembic for database migrations
COPY alembic/ ./alembic/
COPY alembic.ini .

# Expose port (Render will set this via $PORT environment variable)
EXPOSE 8000

# Start command - Run from app.main module
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
