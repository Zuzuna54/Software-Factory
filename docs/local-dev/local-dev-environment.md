# Local Development Environment

This document provides instructions for setting up and using the local development environment for the Software Factory project using Docker Compose.

## Overview

The development environment uses Docker Compose to set up the following services:

- **PostgreSQL**: Database for storing agent data and artifacts with pgvector extension for vector operations
- **Redis**: Message broker for Celery task queue
- **pgAdmin**: Web-based PostgreSQL management tool
- **API**: FastAPI-based backend service
- **Celery Worker**: Background task processing
- **Dashboard**: Next.js-based frontend dashboard

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- Git

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd software-factory
```

### 2. Environment Variables

Copy the example environment file:

```bash
cp .env.example .env.docker
```

Edit `.env.docker` file to configure your environment variables (default values should work for local development).

### 3. Start the Development Environment

```bash
docker-compose up -d
```

This will start all services in the background. To see logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
```

### 4. Access Services

- **API**: [http://localhost:8000](http://localhost:8000)
  - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Dashboard**: [http://localhost:3000](http://localhost:3000)
- **pgAdmin**: [http://localhost:5050](http://localhost:5050)
  - Username: `admin@example.com`
  - Password: `admin`
  - To connect to the PostgreSQL database, create a new server with:
    - Host: `postgres`
    - Port: `5432`
    - Username: `postgres`
    - Password: `postgres`
    - Database: `software_factory`

### 5. Database Migrations

Migrations are automatically applied when the API service starts, but you can run them manually:

```bash
docker-compose exec api alembic upgrade head
```

To create a new migration:

```bash
docker-compose exec api alembic revision --autogenerate -m "Description of changes"
```

### 6. Stopping the Environment

```bash
docker-compose down
```

To remove volumes (will delete all data):

```bash
docker-compose down -v
```

## Development Workflow

### API Development

- The API server runs with hot-reloading enabled.
- Make changes to the Python code in the `agents` directory, and the server will automatically reload.
- Access the API documentation at [http://localhost:8000/docs](http://localhost:8000/docs) to test endpoints.

### Dashboard Development

- The Next.js dashboard also supports hot-reloading.
- Make changes to the JavaScript/TypeScript code in the `dashboard` directory to see changes reflected in real-time.

### Background Tasks

- Celery tasks are defined in `agents/tasks.py`.
- Tasks can be scheduled or triggered via the API.

## Vector Search Capabilities

Our system uses pgvector for storing and querying embeddings:

- Vector columns use the `halfvec(3072)` type optimized for high-dimensional vectors
- HNSW indexes are created for efficient similarity search
- Configured with parameters `m=16` and `ef_construction=64` for optimal performance

## Common Issues

- **Database connection errors**: Ensure PostgreSQL has fully started before the API tries to connect. This should be handled by the health checks, but in rare cases might need a manual restart of the API service:

  ```bash
  docker-compose restart api
  ```

- **Port conflicts**: If you have services already running on the specified ports, edit the `docker-compose.yml` file to use different port mappings.

- **pgvector compatibility**: Make sure you're using PostgreSQL 16 with pgvector extension 0.8.0+ which supports `halfvec` type for high-dimensional vectors.

## Switching Between Docker and Local

To switch between Docker and local development environments:

```bash
./scripts/switch-env.sh docker  # Switch to Docker environment
./scripts/switch-env.sh local   # Switch to local environment
```

## Next Steps

Refer to the project's main README and documentation for more details on the application architecture and development guidelines.
