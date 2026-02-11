FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ /app/

# Create data directories as volumes
RUN mkdir -p /data/db /data/resources /data/uploads

# Environment variables for container paths
ENV DATABASE_DIR=/data/db
ENV RESOURCES_DIR=/data/resources
ENV UPLOADS_DIR=/data/uploads
ENV FLASK_ENV=production

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
