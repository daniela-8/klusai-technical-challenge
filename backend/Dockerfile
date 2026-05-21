FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by lxml and chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create persistent data directory
RUN mkdir -p data/chromadb

EXPOSE 8000

# Run with a single worker — the pipeline uses an asyncio-level lock,
# so multiple workers would each have independent lock state.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
