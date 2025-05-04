# Proposed Project File Structure

This document outlines the proposed file and directory structure for the autonomous AI software development system.

```
software-factory/
├── app/                      # FastAPI application core
│   ├── api/                  # API Endpoints (routers)
│   │   └── endpoints/
│   ├── core/                 # Core configuration, settings
│   ├── models/               # Pydantic models (request/response)
│   ├── services/             # Business logic
│   └── main.py               # FastAPI app entrypoint
├── agents/                   # Core AI Agent implementations
│   ├── base_agent.py         # Base class for all agents
│   ├── communication/        # Agent communication protocol
│   │   └── protocol.py
│   ├── db/                   # Database interaction
│   │   └── postgres.py
│   ├── devops/               # DevOps agent specifics
│   │   ├── cloud/            # Cloud provider integrations (gcp.py, etc.)
│   │   ├── cicd/             # CI/CD management
│   │   ├── deployment/       # Deployment strategies
│   │   ├── iac/              # Infrastructure as Code
│   │   └── monitoring/       # Monitoring integrations
│   ├── git/                  # Git client
│   │   └── git_client.py
│   ├── learning/             # Self-improvement/learning components
│   │   └── experience_collector.py
│   ├── llm/                  # LLM provider integrations
│   │   ├── base.py
│   │   ├── anthropic_provider.py
│   │   └── ...
│   ├── logging/              # Enhanced logging/thought capture
│   │   ├── enhanced_logger.py
│   │   └── thought_capture.py
│   ├── memory/               # Shared memory and vector search
│   │   ├── enhanced_vector_memory.py
│   │   └── search.py
│   ├── metrics/              # Metrics collection
│   │   ├── collector.py
│   │   └── exporters/
│   ├── modification/         # Code modification utilities
│   │   └── context_aware_editor.py
│   ├── notifications/        # Notification service
│   │   └── service.py
│   ├── orchestration/        # Task orchestration, meetings, ceremonies
│   │   ├── ceremonies.py
│   │   ├── meetings.py
│   │   ├── portfolio_manager.py
│   │   └── task_manager.py   # (Likely integrated with Celery)
│   ├── planning/             # Planning components
│   │   └── advanced_planner.py
│   ├── quality/              # Code quality, tech debt, security
│   │   ├── code_analyzer.py
│   │   ├── performance_analyzer.py
│   │   ├── security_reviewer.py
│   │   └── tech_debt_manager.py
│   ├── specialized/          # Specific agent roles
│   │   ├── product_manager.py
│   │   ├── scrum_master.py
│   │   ├── backend_developer.py
│   │   ├── qa_agent.py
│   │   ├── devops_agent.py
│   │   ├── codebase_analysis_agent.py
│   │   ├── frontend_developer_agent.py # (Python control part)
│   │   ├── designer_agent.py           # (Python control part)
│   │   ├── technical_lead_agent.py
│   │   ├── code_review_agent.py
│   │   ├── database_designer_agent.py
│   │   ├── data_science_agent.py
│   │   └── mobile_developer_agent.py   # (Python control part)
│   ├── tasks/                # Celery tasks
│   │   ├── celery_app.py
│   │   └── agent_tasks.py
│   └── __init__.py
├── frontend/                 # Next.js frontend application
│   ├── app/
│   ├── components/
│   ├── public/
│   ├── styles/
│   ├── package.json
│   └── ...
├── tests/                    # Pytest test suite
│   ├── agents/
│   ├── app/
│   └── conftest.py
├── docs/                     # Documentation
│   ├── blueprint.md
│   ├── phases/
│   ├── architecture/         # Architecture specific docs
│   │   ├── file_structure.md # This file
│   │   └── dependencies.md   # Dependencies list
│   └── DEPENDENCIES.md       # Justification for dependencies (as per rule)
├── .github/
│   └── workflows/
├── .env                      # Environment variables
├── alembic/                  # Alembic migration scripts
│   ├── versions/
│   └── env.py
├── alembic.ini               # Alembic configuration
├── pyproject.toml            # Python dependencies (using Poetry or similar)
├── package-lock.json         # Frontend dependency lock file (if using npm)
├── pnpm-lock.yaml            # Frontend dependency lock file (if using pnpm)
└── README.md
```

## Key Directory Explanations:

- **`app/`**: Contains the core FastAPI backend application code, following standard practices.
- **`agents/`**: Houses all the AI agent logic, separated by function (communication, db, llm, memory, specialized roles, etc.).
- **`frontend/`**: Contains the Next.js frontend application.
- **`tests/`**: Holds the automated tests for both backend and potentially frontend components.
- **`docs/`**: All project documentation, including the blueprint, phase details, and architectural documents.
  - **`docs/architecture/`**: Specific documents detailing architectural decisions, structure, and dependencies.
  - **`docs/DEPENDENCIES.md`**: Reserved for justifications per the `dependency-audit` rule.
- **`alembic/` & `alembic.ini`**: Standard directories and configuration for Alembic database migrations.
- **`pyproject.toml` / `package.json`**: Standard dependency management files for Python and Node.js respectively.
- **`.github/`**: For GitHub Actions workflows (CI/CD).
- **`.env`**: For storing environment variables (should be in `.gitignore`).
