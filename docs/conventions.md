# Development Conventions

This document outlines the coding and development conventions for the Autonomous AI Development Team project.

## Code Style

### Python

- Follow PEP 8 style guide
- Use Black for formatting
- Maximum line length: 88 characters
- Use type hints for all function parameters and return values
- Use docstrings for all classes and functions

### JavaScript/TypeScript

- Follow Airbnb JavaScript Style Guide
- Use Prettier for formatting
- Use ESLint for linting
- Use TypeScript interfaces for all data structures
- Use JSDoc comments for all functions

## Git Workflow

- Use feature branches for all changes
- Branch naming: `feature/[feature-name]` or `fix/[issue-name]`
- Commit messages: Follow Conventional Commits format
  - `feat: add new feature`
  - `fix: resolve bug in feature`
  - `docs: update documentation`
  - `chore: update dependencies`
- Create pull requests for all changes
- Required PR approvals: 1

## Testing

- All code should have unit tests
- Minimum test coverage: 80%
- Integration tests for critical paths
- Test naming: `test_[what_is_being_tested].py`

## Documentation

- All public APIs must be documented
- Update documentation with code changes
- Use Markdown for documentation
- Keep documentation in the `docs/` directory
