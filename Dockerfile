# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PYTHONPATH=/app
ENV PROJECT_ID=ccibt-hack25ww7-750
ENV GOOGLE_CLOUD_PROJECT=ccibt-hack25ww7-750
ENV GCP_PROJECT_ID=ccibt-hack25ww7-750
ENV GOOGLE_CLOUD_LOCATION=us-central1
ENV FLASK_DEBUG=false

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY ui/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agents directory (needed for ADK agent imports)
COPY agents/ ./agents/

# Copy the UI application
COPY ui/app.py ./app.py
COPY ui/templates/ ./templates/

# Copy the bigquery_adk_agent for .env file
COPY bigquery_adk_agent/.env ./bigquery_adk_agent/.env

# Expose port
EXPOSE 8080

# Run the application with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
