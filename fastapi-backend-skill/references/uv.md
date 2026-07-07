# uv Version Management Reference

Use this reference when setting up Python version management, dependency management, lockfiles, or project commands.

## Rules

- Use `uv` as the single tool for Python version selection, dependency management, virtual environment management, lockfile generation, and command execution.
- Prefer `pyproject.toml` and `uv.lock` over `requirements.txt`.
- Keep `.python-version` in the project root for the selected Python version.
- Do not add Poetry, Pipenv, or ad hoc dependency workflows to new projects.
- If an existing project already has compatibility files such as `requirements.txt`, preserve them only when required by deployment, and make `pyproject.toml` plus `uv.lock` the source of truth.

## New Project Setup

```bash
uv init --package
uv python pin 3.12
uv add fastapi uvicorn[standard] pydantic-settings sqlalchemy asyncpg alembic
uv add --dev pytest pytest-asyncio httpx ruff mypy
uv lock
```

## Required Root Files

- `.python-version`
- `pyproject.toml`
- `uv.lock`

## Suggested `pyproject.toml` Sections

```toml
[project]
name = "fastapi-backend"
version = "0.1.0"
requires-python = ">=3.12"

[dependency-groups]
dev = [
  "httpx",
  "mypy",
  "pytest",
  "pytest-asyncio",
  "ruff",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Common Commands

```bash
uv sync
uv run uvicorn app.main:app --reload
uv run alembic upgrade head
uv run pytest
uv run ruff check .
uv run mypy app
```

## Dependency Changes

Use these commands instead of editing lockfiles manually:

```bash
uv add <package>
uv add --dev <package>
uv remove <package>
uv lock
```

## Notes

- Commit `uv.lock` for applications.
- Run tools through `uv run` so they use the locked project environment.
- When adding a dependency in code, update `pyproject.toml` and regenerate `uv.lock`.
- Keep deployment documentation aligned with uv commands.
