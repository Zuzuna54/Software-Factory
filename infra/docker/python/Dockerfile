FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi==0.110.0 \
    uvicorn==0.27.1 \
    sqlalchemy==2.0.28 \
    asyncpg==0.29.0 \
    pgvector==0.2.4 \
    celery==5.3.6 \
    redis==5.0.1 \
    psycopg2-binary==2.9.9 \
    pydantic==2.5.3 \
    pygit2==1.13.3

ENV PYTHONPATH=/app 