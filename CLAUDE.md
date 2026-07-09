# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains reusable skill definitions for scaffolding Python backend projects. It is **not** an application — it is a knowledge base of coding standards and templates. Each subdirectory is a self-contained skill with a top-level `SKILL.md` and supporting reference documents.

- `fastapi-backend-skill/` — Conventions for new FastAPI + PostgreSQL + SQLAlchemy projects.
- `flask-backend-skill/` — Conventions for new Flask + PostgreSQL + Flask-SQLAlchemy projects.

## Skill Format

Each skill follows the same layout:

1. `SKILL.md` at the skill root is the entry point. It declares `name`, `description`, and other frontmatter fields.
2. `references/` contains the detailed implementation templates and examples.
3. `evals/` may contain evaluation data for skill quality.

When asked to scaffold a project, always read the relevant skill's `SKILL.md` first, then load only the reference files needed for the immediate task. Do not copy all references indiscriminately.

## FastAPI Skill (`fastapi-backend-skill/`)

Use for FastAPI + PostgreSQL backends.

Core architectural decisions are documented in `fastapi-backend-skill/SKILL.md`. Read these reference files for implementation specifics:

- `references/factory-and-config.md` — App factory, lifespan, and multi-environment settings.
- `references/uv.md` — Python version, `uv` dependency management, and project commands.
- `references/database.md` — SQLAlchemy engine/session setup, transaction boundaries, PostgreSQL.
- `references/alembic.md` — Alembic async configuration and migration commands.
- `references/routing.md` — Centralized route registration without decorators.
- `references/module-template.md` — New domain module scaffolding.
- `references/responses.md` — `ApiResponse`, `ok(...)`, `error(...)`, pagination.
- `references/exceptions.md` — Application errors and global exception handlers.
- `references/logging.md` — Centralized logging, request IDs, ASGI middleware.
- `references/health.md` — Health and readiness endpoints.
- `references/testing.md` — pytest conventions and fixtures.
- `references/security.md` — CORS, trusted hosts, secrets, password handling, log redaction.

Key non-obvious rules to keep in mind:

- Engines must be created inside `lifespan`, never at module import.
- Routes must be registered through the central registry; do not use `@router` decorators.
- Responses must use the shared `ApiResponse` envelope; errors must go through the shared `error(...)` helper.
- Health (`/health`) must not touch the database; readiness (`/ready`) checks dependencies.

## Flask Skill (`flask-backend-skill/`)

Use for Flask + PostgreSQL + Flask-SQLAlchemy backends, including APScheduler-based task scheduling.

Core architectural decisions are documented in `flask-backend-skill/SKILL.md`. Read these reference files for implementation specifics:

- `references/config.md` — Config classes and `.env.example` template.
- `references/migrate.md` — Flask-Migrate (Alembic) rules and commands.
- `references/models.md` — `BaseModel` template and SQLAlchemy 2.0 annotated style.
- `references/exceptions.md` — Unified exception classes and global error handlers.
- `references/responses.md` — `code/message/data` response shape.
- `references/logger.md` — Loguru configuration and Flask logger bridge.
- `references/gunicorn-config.md` — Production Gunicorn configuration template.
- `references/scheduler-architecture.md` — Standalone APScheduler process design.
- `references/scheduler-api.md` — Flask-side scheduler management API.

Key non-obvious rules to keep in mind:

- `app/__init__.py` must expose `create_app()`; config must come from root `.env` + environment variables.
- All migrations must use Flask-Migrate (`flask db migrate` / `flask db upgrade`); never use `db.create_all()`.
- Use `db.session.query(Model).filter_by(...)` syntax; do not use `Model.query`.
- The scheduler must run as a separate process (`scripts/run_scheduler.py`) using `BlockingScheduler` and `SQLAlchemyJobStore`; never run it inside the Flask web process.
- Web logs and scheduler logs must be separate files.
- All fields require `comment="..."` except `relationship()` declarations, which must never use `comment`.

## Common Commands

There are no global build, test, or lint commands in this repository because it is a knowledge base, not a runnable project. When applying a skill to scaffold a project, use the commands documented in that skill's references (typically `uv` for Python and dependency management, `pytest` for testing, and project-specific `flask`/`alembic` commands for migrations).

## Editing Guidelines

- When adding or updating a skill, keep the same frontmatter structure and reference file organization as the existing skills.
- Only reference files that are directly needed for implementation should be written; avoid duplicating overview material that belongs in `SKILL.md`.
- When updating a reference template, keep the code copy-pasteable and self-contained; these files are meant to be pasted into generated projects.
