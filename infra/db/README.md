# PostgreSQL Database Schema

This directory contains the database schema implementation for the Autonomous AI Development Team project. The schema is implemented using SQLAlchemy models and Alembic for migrations.

## Directory Structure

- `models/` - SQLAlchemy model definitions
  - `base.py` - Base class and common utilities
  - `core.py` - Core system models (agents, messages, activities, etc.)
  - `artifacts.py` - Artifact-specific models
  - `__init__.py` - Package exports
- `migrations/` - Alembic migration scripts
  - `versions/` - Migration version files
  - `env.py` - Alembic environment configuration
  - `alembic.ini` - Alembic configuration
  - `script.py.mako` - Migration script template

## Database Schema

The schema includes the following tables:

### Core System Tables

- `agents` - Agent metadata and capabilities
- `agent_messages` - Inter-agent communication
- `agent_activities` - Agent actions and decisions
- `artifacts` - General artifact storage
- `tasks` - Task definitions and assignments
- `meetings` - Agile ceremony records
- `meeting_conversations` - Conversation details within meetings

### Artifact-Specific Tables

- `requirements_artifacts` - User stories, features, requirements
- `design_artifacts` - Wireframes, architecture diagrams
- `implementation_artifacts` - Code implementations
- `testing_artifacts` - Test cases and results
- `project_vision` - Vision statements
- `project_roadmap` - Project timeline and milestones
- `codebase_analysis` - Analysis of existing codebases
- `detected_patterns` - Patterns detected in existing codebases

## PostgreSQL Extensions

The schema requires the following PostgreSQL extensions:

- `uuid-ossp` - For UUID generation
- `pgvector` - For vector embeddings and similarity search

## Running Migrations

### Prerequisites

- PostgreSQL 16 or higher with pgvector extension
- Python 3.12 or higher
- Required Python packages: SQLAlchemy, alembic, asyncpg, pgvector

### Setting up the database

1. Create a PostgreSQL database:

```bash
createdb autonomous_ai_dev
```

2. Apply migrations:

```bash
# From the project root directory
alembic upgrade head
```

### Creating new migrations

To create a new migration after modifying the models:

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Environment variables

The migration scripts use the `DATABASE_URL` environment variable. If not set, it defaults to:

```
postgresql+asyncpg://postgres:postgres@localhost/autonomous_ai_dev
```

You can override this by setting the environment variable:

```bash
export DATABASE_URL="postgresql+asyncpg://username:password@hostname/dbname"
```

## Docker Environment

If using Docker, the database setup is handled by the Docker Compose configuration. The migrations will be applied when the application container starts.

See the root `docker-compose.yml` file for database configuration details.
