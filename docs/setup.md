# Setup Instructions

This document describes how to set up the Autonomous AI Development Team project for local development.

## Prerequisites

- Docker and Docker Compose
- Git
- Python 3.12 (for local development outside Docker)
- Node.js 20 (for local development outside Docker)

## Local Development Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Start the Docker Compose environment:

   ```bash
   docker-compose up -d
   ```

3. Initialize the database:

   ```bash
   docker-compose exec postgres psql -U agent_user -d agent_team -f /docker-entrypoint-initdb.d/init.sql
   ```

4. Access the Python development container:

   ```bash
   docker-compose exec python bash
   ```

5. Access the Node.js development container:
   ```bash
   docker-compose exec node sh
   ```

## Cloud Deployment

See `docs/cloud_setup.md` for instructions on deploying to Google Cloud Platform.
