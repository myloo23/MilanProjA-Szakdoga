# Fixed Python base image for reproducible builds
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de AS base

# Show logs immediately and don't create .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create a non-root user for security
RUN useradd --create-home --uid 10001 appuser

# Working directory inside the container
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
# Copy the application source code
COPY app/ ./app/

# Run the application as the non-root user
USER appuser

# Application listens on port 8000
EXPOSE 8000

# Check every 10s if the application is healthy
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"

# Start Gunicorn with 2 workers and 4 threads per worker
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "app.app:app"]