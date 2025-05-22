# Setup Instructions

This document provides instructions for setting up the Software Factory project for local development and deployment.

## Prerequisites

- Python 3.12+
- Node.js 20+ (for the dashboard)
- PostgreSQL 16+ with pgvector 0.8.0+
- Redis
- Docker and Docker Compose (optional)

## Local Development Options

You have two options for setting up your development environment:

1. **Docker-based setup**: Ideal for quick start and consistent environments
2. **Direct local setup**: Better for deeper debugging and customization

## Option 1: Docker-based Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd software-factory
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env.docker
```

Edit `.env.docker` as needed (defaults should work for most users).

### 3. Start Services with Docker Compose

```bash
docker-compose up -d
```

All services will be available:

- API: http://localhost:8000
- Dashboard: http://localhost:3000
- pgAdmin: http://localhost:5050

## Option 2: Direct Local Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd software-factory
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env.local
```

Edit `.env.local` with your local database credentials. At minimum:

```
DATABASE_URL=postgresql://postgres:postgres@localhost/software_factory
```

### 3. Install Dependencies with Pipenv

```bash
pip install pipenv
pipenv install --dev
```

### 4. Set Up Database

Ensure PostgreSQL is running and create the database:

```bash
psql -U postgres -c "CREATE DATABASE software_factory;"
psql -U postgres -d software_factory -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -U postgres -d software_factory -c "CREATE EXTENSION IF NOT EXISTS \"pgvector\";"
```

Verify pgvector version (need 0.8.0+ for halfvec support):

```bash
psql -U postgres -d software_factory -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
```

### 5. Run Migrations

```bash
PYTHONPATH=$PWD pipenv run alembic upgrade head
```

### 6. Start the Backend Server

```bash
PYTHONPATH=$PWD pipenv run python -m uvicorn agents.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Set Up and Run the Dashboard (optional)

```bash
cd dashboard
npm install
npm run dev
```

## Automated Setup Script

For convenience, we provide a setup script:

```bash
chmod +x scripts/setup-local-dev.sh
./scripts/setup-local-dev.sh
```

And a script to ensure services are running:

```bash
chmod +x scripts/start-services.sh
./scripts/start-services.sh
```

## Database Schema

The database schema includes:

- **Agent Tables**: `agents`, `agent_messages`, `agent_activities`
- **Planning Tables**: `tasks`, `meetings`, `meeting_conversations`
- **Artifact Tables**: `artifacts`, `requirements_artifacts`, `design_artifacts`, `implementation_artifacts`, `testing_artifacts`, `project_vision`, `project_roadmap`

## Vector Support

The system uses pgvector with halfvec type for efficient vector operations:

- Supports 3072-dimensional vectors for embedding storage
- Uses HNSW indexes for similarity searches
- Key vector columns:
  - `agent_messages.context_vector`: halfvec(3072)
  - `artifacts.content_vector`: halfvec(3072)

## Switching Environments

To switch between Docker and local environments:

```bash
./scripts/switch-env.sh docker  # Switch to Docker configuration
./scripts/switch-env.sh local   # Switch to local configuration
```
