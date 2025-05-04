# Proposed Project Dependencies

This document lists the key proposed libraries for the project, categorized by backend (Python) and frontend (TypeScript/Next.js).

## Python Backend Dependencies

- **Web Framework:** `fastapi`, `uvicorn[standard]`
- **LLM Interaction:** `google-cloud-aiplatform` (for Vertex AI Gemini models)
- **Database ORM:** `sqlalchemy[asyncio]`, `asyncpg` (PostgreSQL async driver)
- **Database Migrations:** `alembic`
- **Vector Database:** `pgvector` (Python integration, often used via SQLAlchemy extension)
- **Task Queue:** `celery`, `redis` (as broker/backend)
- **Data Validation/Serialization:** `pydantic` (comes with FastAPI)
- **Asynchronous HTTP Client:** `httpx`
- **Configuration:** `python-dotenv`
- **Testing:** `pytest`, `pytest-asyncio`, `httpx` (for testing FastAPI)
- **Git Interaction:** `GitPython` (or use `subprocess`)
- **Cloud SDKs:** `google-cloud-sdk`, `boto3` (AWS), `azure-sdk-for-python` (as needed based on deployment target)
- **Logging:** Standard `logging`, potentially `loguru` for enhanced features.
- **Data Science (Iter. 10):** `pandas`, `scikit-learn`, `numpy`
- **Metrics:** `prometheus-client` (if using Prometheus for monitoring)

_Note: Specific versions should be pinned in `pyproject.toml` or `requirements.txt`._

## Frontend Dependencies (TypeScript/Next.js)

- **Framework:** `next`, `react`, `react-dom`
- **Styling:** `tailwindcss`
- **UI Components:** `shadcn-ui` (managed via CLI), `lucide-react` (icons)
- **State Management:** `@reduxjs/toolkit`, `react-redux`, `zustand` (select based on need)
- **API Fetching:** `axios` or built-in `fetch`
- **Real-time:** `socket.io-client`
- **Testing:** `jest`, `@testing-library/react`, `@testing-library/jest-dom`, `playwright` or `cypress` (for E2E tests)
- **Utility:** `clsx`, `tailwind-merge` (often used with shadcn/ui)

_Note: Specific versions should be pinned in `package.json` and managed via `npm`, `yarn`, or `pnpm`._
