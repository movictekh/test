FROM python:3.11.4-slim-bullseye

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install only system deps needed for common Python backends (psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure pre_run script is executable
RUN chmod +x /app/pre_run.sh

ENTRYPOINT ["/app/pre_run.sh"]
CMD ["gunicorn", "bomach_backend.wsgi", "-b", "0.0.0.0:8000"]
