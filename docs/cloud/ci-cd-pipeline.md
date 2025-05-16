# CI/CD Pipeline Documentation

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the Autonomous AI Development Team project.

## Overview

The CI/CD pipeline is implemented using GitHub Actions and consists of several workflows:

1. **Python CI**: For testing and linting Python code (backend)
2. **TypeScript CI**: For testing and linting TypeScript/JavaScript code (frontend)
3. **Database Migrations**: For validating database migrations
4. **Deployment**: For deploying the application to Google Cloud Platform

## Workflow Descriptions

### Python CI (`python-ci.yml`)

This workflow runs when changes are made to Python code in the `agents`, `app`, or `infra/db` directories.

**Jobs:**

1. **Lint**

   - Runs code quality checks using Ruff, Black, and MyPy
   - Ensures code follows style guidelines and type checking passes

2. **Test**
   - Sets up a test PostgreSQL database with required extensions
   - Runs all Python tests with pytest
   - Generates and uploads test coverage reports

### TypeScript CI (`typescript-ci.yml`)

This workflow runs when changes are made to the frontend code in the `dashboard` directory.

**Jobs:**

1. **Lint and Format**

   - Checks code quality with ESLint
   - Verifies TypeScript types
   - Ensures consistent formatting with Prettier

2. **Unit Tests**

   - Runs Jest tests for frontend components
   - Generates and uploads test coverage reports

3. **Build**
   - Builds the Next.js application
   - Uploads build artifacts for potential deployment

### Database Migrations (`db-migrations.yml`)

This workflow validates database migrations when changes are made to the database models or migration scripts.

**Jobs:**

1. **Validate Migrations**
   - Sets up a test database
   - Ensures migrations can be applied successfully
   - Tests both forward (upgrade) and backward (downgrade) migrations

### Deployment (`deploy.yml`)

This workflow deploys the application to Google Cloud Platform when changes are pushed to the main branch.

**Jobs:**

1. **Build and Deploy Backend**

   - Builds the API Docker image
   - Pushes the image to Google Container Registry
   - Deploys to Cloud Run
   - Runs database migrations

2. **Build and Deploy Frontend**
   - Builds the dashboard
   - Creates a Docker image
   - Deploys to Cloud Run

## Setting Up CI/CD

### Prerequisites

To use the CI/CD pipeline, you need to set up the following GitHub secrets:

- `GCP_PROJECT_ID`: Your Google Cloud Platform project ID
- `GCP_SA_KEY`: Service account key JSON for GitHub Actions to authenticate with GCP
- `DATABASE_URL`: Database connection string for deployment
- `REDIS_URL`: Redis connection string for deployment
- `NEXT_PUBLIC_API_URL`: Public URL of the API for the frontend to connect to
- `CODECOV_TOKEN`: (Optional) Token for uploading coverage reports to Codecov

### Local Testing

Before pushing changes, you can run the same checks locally:

```bash
# Python linting and tests
black agents app infra
ruff check agents app infra
mypy agents app infra
pytest --cov=agents --cov=app --cov=infra

# TypeScript linting and tests
cd dashboard
npm run lint
npm run type-check
npm test
npm run build
```

## Continuous Deployment

The deployment workflow is configured to automatically deploy changes from the `main` branch to the staging environment. For production deployments, you can manually trigger the workflow with the `environment` parameter set to `production`.

## Monitoring Deployments

You can monitor the status of deployments in:

1. GitHub Actions tab in the repository
2. Google Cloud Console:
   - Cloud Run for service status
   - Cloud Logging for application logs
   - Cloud Monitoring for performance metrics
