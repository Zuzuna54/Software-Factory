# Setup Instructions

This document describes how to set up the Autonomous AI Development Team project for local development using Docker Compose.

## Prerequisites

- **Docker and Docker Compose:** Ensure you have the latest versions installed. [Install Docker](https://docs.docker.com/get-docker/)
- **Git:** Required for cloning the repository. [Install Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- **Cloud SDK (Optional but Recommended):** `gcloud` CLI if you plan to interact with GCP resources directly or use application default credentials. [Install gcloud](https://cloud.google.com/sdk/docs/install)
- **.env File:** Create a `.env` file in the project root for secrets and configuration. See `.env.example` (to be created) for required variables.

## Local Development Setup Steps

1.  **Clone the Repository:**

    ```bash
    git clone <repository-url>
    cd software-factory # Or your repository name
    ```

2.  **Create `.env` File:**
    Copy `.env.example` (once created) to `.env` and fill in the required values, especially `POSTGRES_PASSWORD` and any necessary API keys (e.g., `GOOGLE_APPLICATION_CREDENTIALS` path if using a service account, or configure ADC).

    ```bash
    cp .env.example .env
    # Edit .env with your details
    ```

    _Note: Ensure `.env` is listed in your `.gitignore` file._

3.  **Build and Start Docker Containers:**
    This command will build the images defined in the Dockerfiles and start the services (PostgreSQL, Redis, backend, frontend).

    ```bash
    docker-compose up --build -d
    ```

    - `--build`: Forces Docker to rebuild the images if Dockerfiles have changed.
    - `-d`: Runs containers in detached mode (in the background).

4.  **Check Container Status:**
    Verify that all containers are running and healthy.

    ```bash
    docker-compose ps
    ```

    You should see `postgres`, `redis`, `backend`, and `frontend` services running.

5.  **Apply Database Migrations (using Alembic - requires setup in later iteration):**
    Once Alembic is configured (see `alembic.ini`), you'll run migrations inside the `backend` container:

    ```bash
    docker-compose exec backend alembic upgrade head
    ```

    _(Initially, the `init.sql` script handles schema creation, but Alembic will manage changes later.)_

6.  **Accessing Services:**

    - **Backend API:** `http://localhost:8000` (or the port mapped in `docker-compose.yml`)
    - **Frontend App:** `http://localhost:3000` (or the port mapped in `docker-compose.yml`)
    - **Database (e.g., using `psql`):**
      ```bash
      docker-compose exec postgres psql -U agent_user -d agent_team
      ```
      (Password: `agent_password` or the value in your `.env` if changed)

7.  **Running Tests:**
    Execute the test suite inside the `backend` container:

    ```bash
    docker-compose exec backend pytest
    ```

8.  **Accessing Shells:**

    - Backend (Python) container:
      ```bash
      docker-compose exec backend bash
      ```
    - Frontend (Node) container:
      ```bash
      docker-compose exec frontend sh # Alpine uses sh
      ```

9.  **Stopping the Environment:**
    ```bash
    docker-compose down
    ```
    To remove volumes (database data, redis data) as well:
    ```bash
    docker-compose down -v
    ```

## Cloud Deployment

See `docs/deployment/gcp_setup.md` (to be created) for instructions on deploying to Google Cloud Platform using Terraform.
