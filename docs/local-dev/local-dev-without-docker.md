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

Edit the `.env.local` file to match your local PostgreSQL and Redis configurations.

### 3. Run the Setup Script

We provide a script that automates most of the setup process:

```bash
chmod +x scripts/setup-local-dev.sh
./scripts/setup-local-dev.sh
```

This script will:

- Verify required dependencies
- Install Python dependencies with pipenv
- Create the PostgreSQL database and enable extensions
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
pipenv run alembic revision -m "description of change"
```

To apply migrations:

```bash
pipenv run alembic upgrade head
```

To revert a migration:

```bash
pipenv run alembic downgrade -1
```

## Environment Variables

The `.env.local` file configures your local environment. Key variables include:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: PostgreSQL connection settings
- `REDIS_HOST`, `REDIS_PORT`: Redis connection settings
- `API_HOST`, `API_PORT`: API server settings
- `DEBUG`: Enable/disable debug mode
- `LOG_LEVEL`: Set logging verbosity

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

1. Verify PostgreSQL is running with `pg_ctl status`
2. Check that the credentials in `.env.local` match your PostgreSQL setup
3. Ensure your PostgreSQL is configured to accept connections from localhost

### Redis Connection Issues

If you have trouble connecting to Redis:

1. Verify Redis is running with `redis-cli ping`
2. Check Redis is listening on the port specified in `.env.local`
3. Ensure no firewall is blocking the Redis port
