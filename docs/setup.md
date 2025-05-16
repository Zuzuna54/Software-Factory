# Setup Instructions

This document provides instructions for setting up the Autonomous AI Development Team project for local development and deployment.

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker and Docker Compose
- Google Cloud SDK (for deployment)
- PostgreSQL 16 (local or via Docker)
- Redis (local or via Docker)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Backend Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows, use .venv\Scripts\activate

# Install dependencies
cd agents
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools

# Set up environment variables
cp .env.example .env
# Edit .env with your local configuration
```

### 3. Frontend Setup

```bash
# Install dependencies
cd dashboard
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your configuration
```

### 4. Database Setup

Using Docker Compose:

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Apply database migrations (once backend is set up)
cd agents
python -m alembic upgrade head
```

### 5. Running Services

```bash
# Run backend API (from agents directory)
python -m uvicorn app.main:app --reload

# Run frontend (from dashboard directory)
npm run dev

# Run Celery workers (from agents directory)
celery -A agents.tasks.celery_app worker --loglevel=info
```

## Docker Compose Setup

For a complete local environment using Docker Compose:

```bash
# Build and start all services
docker-compose up -d

# Apply database migrations
docker-compose exec api python -m alembic upgrade head
```

## Google Cloud Deployment

### 1. GCP Project Setup

```bash
# Set up GCP project
gcloud init
gcloud projects create <project-id>
gcloud config set project <project-id>

# Enable required APIs
gcloud services enable cloudrun.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com
```

### 2. Infrastructure Deployment

```bash
# Create infrastructure using Terraform
cd infra/terraform
terraform init
terraform plan -var="project_id=<project-id>"
terraform apply -var="project_id=<project-id>"
```

### 3. Application Deployment

```bash
# Deploy backend to Cloud Run
gcloud builds submit --config cloudbuild.yaml

# Deploy database migrations
gcloud builds submit --config cloudbuild-migrations.yaml
```

## Additional Configuration

For additional configuration options, see:

- [Agent Configuration](./configuration/agents.md)
- [Database Schema](./database/schema.md)
- [Deployment Options](./deployment/options.md)
- [LLM Provider Setup](./configuration/llm-providers.md)
