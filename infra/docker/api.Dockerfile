FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY agents/requirements.txt agents/requirements.txt
RUN pip install --no-cache-dir --upgrade -r agents/requirements.txt

# Copy project files
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 8000

# Command to run the API server
CMD ["uvicorn", "agents.main:app", "--host", "0.0.0.0", "--port", "8000"] 