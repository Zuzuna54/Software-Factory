FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    # Add any other system dependencies needed for Python packages
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency definition files first for layer caching
# COPY pyproject.toml* requirements.txt* ./ 
# -- Activate one of the following sections once dependency files exist --

# Option 1: Using requirements.txt
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# Option 2: Using Poetry (if pyproject.toml is set up for it)
# COPY pyproject.toml poetry.lock* ./
# RUN pip install --no-cache-dir poetry && \
#     poetry config virtualenvs.create false && \
#     poetry install --no-root --no-dev

# Placeholder: Install basic dependencies listed in docs/architecture/dependencies.md
# Replace this with proper dependency management (Poetry/PDM/pip) once dependency files exist
RUN pip install --no-cache-dir \
    fastapi==0.111.0 \
    uvicorn[standard]==0.29.0 \
    sqlalchemy[asyncio]==2.0.30 \
    asyncpg==0.29.0 \
    alembic==1.13.1 \
    pgvector==0.2.5 \
    celery==5.4.0 \
    redis==5.0.4 \
    pydantic==2.7.1 \
    python-dotenv==1.0.1 \
    httpx==0.27.0 \
    google-cloud-aiplatform==1.53.0 \
    GitPython==3.1.43 \
    pytest==8.2.0 \
    pytest-asyncio==0.23.6
    # Add other dependencies from docs/architecture/dependencies.md as needed

# Copy the rest of the application code
COPY . /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden in docker-compose.yml)
# Keeps the container running for exec or development overrides
CMD ["tail", "-f", "/dev/null"] 