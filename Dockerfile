FROM python:3.13-slim

# Set version as build argument and label
ARG VERSION=0.1.0
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.title="ytdl-sub Config Manager"
LABEL org.opencontainers.image.description="A modular Peloton scraper for ytdl-sub subscriptions"
LABEL org.opencontainers.image.source="https://github.com/owner/ytdl-sub-config-manager"

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config.example.yaml ./
COPY env.example ./

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV RUN_IN_CONTAINER=True

# Create entrypoint script
RUN echo '#!/bin/bash\npython -m src "$@"' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["scrape"]
