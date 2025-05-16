# Local Development Setup without Docker

This guide provides instructions for setting up the Software Factory development environment directly on your local machine without using Docker. This approach can be useful for developers who prefer direct access to services or when Docker isn't feasible.

## Prerequisites

Before you begin, make sure you have the following installed:

1. **Python 3.12+**

   - [Download Python](https://www.python.org/downloads/)

2. **pipenv**

   ```bash
   pip install pipenv
   ```

3. **PostgreSQL 16+**

   - [Download PostgreSQL](https://www.postgresql.org/download/)
   - Make sure to install pgvector 0.8.0+ for vector support
   - `CREATE EXTENSION vector;` in your PostgreSQL instance

4. **Redis**
   - [Download Redis](https://redis.io/download)
   - For macOS: `brew install redis`
   - For Ubuntu: `sudo apt install redis-server`

## Setup Process

### 1. Clone the Repository

```bash
git clone <repository-url>
cd software-factory
```

### 2. Environment Setup

Copy the example environment file and update it with your local settings:

```bash
cp .env.example .env.local
```

Edit the `.env.local` file to match your local PostgreSQL and Redis configurations. At minimum, you need:

```
DATABASE_URL=postgresql://postgres:postgres@localhost/software_factory
```

### 3. Run the Setup Script

We provide a script that automates most of the setup process:

```bash
chmod +x scripts/setup-local-dev.sh
./scripts/setup-local-dev.sh
```

This script will:

- Verify required dependencies
- Install Python dependencies with pipenv
- Create the PostgreSQL database and enable required extensions:
  - uuid-ossp
  - pgvector (requires version 0.8.0+ for halfvec support)
- Test Redis connection
- Set up local storage directories if needed
- Run database migrations

### 4. Start the Services

If PostgreSQL and Redis aren't running, you can start them with:

```bash
chmod +x scripts/start-services.sh
./scripts/start-services.sh
```

### 5. Switch to Local Environment

Use the environment switching script to set up local configuration:

```bash
chmod +x scripts/switch-env.sh
./scripts/switch-env.sh local
```

### 6. Start the Application

```bash
pipenv run start
```

The API will be available at http://localhost:8000

## Development Workflow

### Running Tests

```bash
pipenv run test
```

### Code Quality Checks

```bash
pipenv run quality
```

### Database Migrations

To create a new migration:

```bash
PYTHONPATH=$PWD pipenv run alembic revision -m "description of change"
```

To apply migrations:

```bash
PYTHONPATH=$PWD pipenv run alembic upgrade head
```

To revert a migration:

```bash
PYTHONPATH=$PWD pipenv run alembic downgrade -1
```

## Database Vector Support

Our system uses high-dimensional vectors (3072 dimensions) for semantic search capabilities:

1. We use pgvector's `halfvec` type for efficient storage of embeddings
2. HNSW indexes are created for fast similarity searches
3. Key vector columns:
   - `agent_messages.context_vector`: halfvec(3072)
   - `artifacts.content_vector`: halfvec(3072)

Make sure your PostgreSQL has pgvector 0.8.0+ installed to support the `halfvec` type.

## Environment Variables

The `.env.local` file configures your local environment. Key variables include:

- `DATABASE_URL`: PostgreSQL connection string (format: `postgresql://user:password@host/dbname`)
- `REDIS_URL`: Redis connection string
- `API_HOST`, `API_PORT`: API server settings
- `DEBUG`: Enable/disable debug mode
- `LOG_LEVEL`: Set logging verbosity
- `GEMINI_API_KEY`, `GEMINI_PROJECT`, `GEMINI_LOCATION`: Gemini AI configuration

## Switching Between Docker and Local Development

If you need to switch between Docker and local development:

1. For Docker:

   ```bash
   ./scripts/switch-env.sh docker
   ```

2. For Local Development:
   ```bash
   ./scripts/switch-env.sh local
   ```

The script will copy the appropriate environment file to `.env` and preserve changes.

## Troubleshooting

### PostgreSQL Connection Issues

If you encounter PostgreSQL connection errors:

1. Verify PostgreSQL is running with `pg_ctl status` or `pg_isready`
2. Check that the credentials in `.env.local` match your PostgreSQL setup
3. Make sure the `software_factory` database exists
4. Confirm the pgvector extension is installed with `SELECT * FROM pg_extension WHERE extname = 'vector';`

### Vector Support Issues

If you encounter errors related to vectors:

1. Check your pgvector version: `SELECT extversion FROM pg_extension WHERE extname = 'vector';`
2. Make sure it's 0.8.0+ for `halfvec` support
3. You may need to recreate the database or manually run the migration that converts vectors to halfvec
