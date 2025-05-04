# Development Conventions

This document outlines the coding and development conventions for the Autonomous AI Development Team project.

## Code Style

### Python (Backend & Agents)

- **Style Guide:** Strictly follow [PEP 8](https://www.python.org/dev/peps/pep-0008/).
- **Formatter:** Use [Black](https://github.com/psf/black) with default settings (line length 88).
- **Linter:** Use [Ruff](https://github.com/astral-sh/ruff) for linting and import sorting. Configure Ruff in `pyproject.toml`.
- **Type Hinting:** Use type hints for all function/method parameters and return values ([PEP 484](https://www.python.org/dev/peps/pep-0484/)).
- **Docstrings:** Use Google-style docstrings ([PEP 257](https://www.python.org/dev/peps/pep-0257/)) for all modules, classes, and functions/methods.
- **Imports:** Use absolute imports where possible. Ruff will manage import sorting.
- **Naming:**
  - `snake_case` for variables, functions, methods, modules.
  - `PascalCase` for classes.
  - `UPPER_SNAKE_CASE` for constants.

### TypeScript (Frontend - Next.js)

- **Style Guide:** Follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript) adapted for TypeScript.
- **Formatter:** Use [Prettier](https://prettier.io/) configured in `.prettierrc`.
- **Linter:** Use [ESLint](https://eslint.org/) with recommended TypeScript and React plugins, configured in `.eslintrc.js`.
- **Type System:** Leverage TypeScript's static typing. Avoid `any` where possible. Use interfaces or types for object shapes.
- **Component Structure:** Use functional components with Hooks.
- **Naming:**
  - `camelCase` for variables, functions.
  - `PascalCase` for components, interfaces, types, enums.

## Git Workflow

- **Branching Strategy:** Use a feature branching model (e.g., Gitflow simplified).
  - `main`: Production-ready code.
  - `develop`: Integration branch for features.
  - `feature/<feature-name>`: Branches for new features.
  - `fix/<issue-name>`: Branches for bug fixes.
- **Commit Messages:** Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.
  - Examples: `feat: Implement user login endpoint`, `fix: Correct calculation error in billing`, `docs: Update agent communication protocol`, `chore: Upgrade fastapi dependency`, `refactor: Simplify database query logic`, `test: Add unit tests for payment service`.
- **Pull Requests (PRs):**
  - All changes must be submitted via PRs targeting the `develop` branch (or `main` for hotfixes).
  - PRs should be small and focused on a single logical change.
  - PR descriptions should clearly explain the change and link to related tasks or issues.
  - Require at least one approval from a Lead agent (or human reviewer if applicable).
  - CI checks (linting, testing) must pass before merging.

## Testing

- **Python:** Use `pytest` for all backend and agent tests.
  - Organize tests in the `tests/` directory, mirroring the structure of the code being tested (e.g., `tests/agents/specialized/test_product_manager.py`).
  - Use `pytest-asyncio` for testing async code.
  - Aim for >= 90% test coverage (as per project overview).
  - Include unit, integration, and potentially end-to-end tests.
- **TypeScript:** Use `jest` with `@testing-library/react` for frontend component tests.
  - Organize tests alongside components (`*.test.tsx`) or in a `__tests__` directory.
  - Consider `Playwright` or `Cypress` for end-to-end testing.
  - Aim for >= 90% test coverage.

## Documentation

- **Code Documentation:** Use docstrings (Google style for Python, JSDoc for TypeScript) for all public modules, classes, functions, and complex logic.
- **Project Documentation:** Maintain comprehensive documentation in the `docs/` directory using Markdown.
  - Keep `blueprint.md` updated as the high-level guide.
  - Update `docs/phases/` documents if implementation deviates significantly from the plan.
  - Maintain architectural documents in `docs/architecture/`.
  - Use `docs/DEPENDENCIES.md` strictly for justifying _new_ dependencies.
- **Diagrams:** Use Mermaid syntax (`.mmd` files) in `docs/diagrams/` to support architectural documentation, following the `docs-guidelines` rule.

## Dependency Management

- **Python:** Use `pyproject.toml` (preferably with Poetry or PDM) to manage dependencies. Pin exact versions.
- **Frontend:** Use `package.json` with `pnpm` (as per project overview). Use `pnpm-lock.yaml` to lock exact versions.
- **Adding Dependencies:** Follow the `dependency-audit` rule: check for existing similar functionality, get Lead approval, and justify in `docs/DEPENDENCIES.md`.

## Error Handling

- Define consistent error handling patterns for both backend and frontend.
- Use appropriate HTTP status codes in API responses.
- Log errors effectively with sufficient context.
