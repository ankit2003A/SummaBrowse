# Use official Python slim image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Set environment variables for noninteractive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p uploads output downloads

# Expose port
EXPOSE 5000

# Set environment variables for Flask
ENV HOST=0.0.0.0
ENV PORT=5000

# Run with Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--timeout", "600", "--workers", "1"] 