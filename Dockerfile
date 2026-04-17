# Use official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# libpq-dev is often needed for psycopg2 (PostgreSQL adapter)
# gcc might be needed for building some python packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install python dependencies
# First, install Torch CPU-only to save ~2GB of space and stay within memory limits
RUN pip install --no-cache-dir torch==2.1.0 transformers==4.35.0 --extra-index-url https://download.pytorch.org/whl/cpu

# Install the rest of the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-cache ML models during build to make deployment instant
# This downloads gpt2 and detoxify models into the image
RUN python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('gpt2'); from detoxify import Detoxify; Detoxify('original')"

# Copy the rest of the application
COPY . .

# Expose port 8000
EXPOSE 8000

# Command to run the application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
