# AGENTS.md

This file provides guidance to AI coding agents (omp) when working with code in this repository.

## Repository Overview

This repository contains reusable skill definitions — Python backend scaffolding conventions, content tooling, exam restoration, and a full development pipeline. It is **not** an application — it is a knowledge base of coding standards and templates. Most skill subdirectories are self-contained: a top-level `SKILL.md` plus supporting reference documents.

- `fastapi-backend-skill/` — Conventions for new FastAPI + PostgreSQL + SQLAlchemy projects.
- `flask-backend-skill/` — Conventions for new Flask + PostgreSQL + Flask-SQLAlchemy projects.
- `url-summary-to-html-skill/` — Conventions for summarizing provided URLs into a self-contained HTML page saved in the current directory.
- `exam-paper-restoration/` — Conventions for restoring clean, blank, authentic exam questions and geometric diagrams from messy photos.
- `dev-flow/` — One-command full development pipeline: grill → spec → tickets → per-ticket sub-agent implementation → code-review → retro. Single-file skill; it chains other skills installed under `~/.claude/skills/` (symlinks are managed by the user).
- `agents/ticket-implementer.md` — Sub-agent definition (symlinked into `~/.claude/agents/`) that implements exactly one tracer-bullet ticket with TDD, then commits.

## Skill Format

Each skill follows the same layout:

1. `SKILL.md` at the skill root is the entry point. It declares `name`, `description`, and other frontmatter fields.
2. `references/` contains the detailed implementation templates and examples.
3. `evals/` may contain evaluation data for skill quality.

When asked to scaffold a project, always read the relevant skill's `SKILL.md` first, then load only the reference files needed for the immediate task. Do not copy all references indiscriminately.

Exception: `dev-flow/SKILL.md` is a single-file pipeline skill with no `references/`; it orchestrates other skills installed under `~/.claude/skills/` (`to-spec`, `to-tickets`, `code-review`, `retro`).

## FastAPI Skill (`fastapi-backend-skill/`)

Use for FastAPI + PostgreSQL backends.

Core architectural decisions are documented in `fastapi-backend-skill/SKILL.md`. Read these reference files for implementation specifics:

- `references/factory-and-config.md` — App factory, lifespan, and multi-environment settings.
- `references/uv.md` — Python version, `uv` dependency management, and project commands.
- `references/database.md` — SQLAlchemy engine/session setup, transaction boundaries, PostgreSQL.
- `references/alembic.md` — Alembic async configuration and migration commands.
- `references/routing.md` — Centralized route registration without decorators.
- `references/module-template.md` — Tiered domain scaffolding: single-file domain → domain package → full domain.
- `references/responses.md` — `ApiResponse`, `ok(...)`, `error(...)`, pagination.
- `references/exceptions.md` — Application errors and global exception handlers.
- `references/logging.md` — Centralized logging, request IDs, ASGI middleware.
- `references/health.md` — Health and readiness endpoints.
- `references/testing.md` — pytest conventions and fixtures.
- `references/security.md` — CORS, trusted hosts, secrets, password handling, log redaction.
- `references/authentication.md` — JWT/OAuth2 password authentication, token issuance, and `CurrentUser` dependency.
- `references/streaming.md` — SSE, JSON Lines, byte streaming, and `RouteSpec.response_class`.

Key non-obvious rules to keep in mind:

- Engines must be created inside `lifespan`, never at module import.
- Routes must be registered through the central registry (`app/api/router.py`); never use `@router`/`@app` decorators.
- API implementations live under `app/api/v1/`. New domains start as a single module `app/api/v1/<domain>.py`; promote to a package (`endpoints.py`/`routes.py`/`schemas.py`, plus `service.py` only for complex domains) on growth triggers, never preemptively.
- ORM models never live in domain files. They go to `app/models/<domain>.py` and are re-exported from `app/models/__init__.py`, which `app/db/base.py` imports once for Alembic discovery.
- No `repository.py` by default. Add `service.py` only when the domain has reusable business rules or multi-step transaction orchestration.
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

Key non-obvious rules:

- `app/__init__.py` must expose `create_app()`; config must come from root `.env` + environment variables.
- All migrations must use Flask-Migrate (`flask db migrate` / `flask db upgrade`); never use `db.create_all()`.
- Use `db.session.query(Model).filter_by(...)` syntax; do not use `Model.query`.
- The scheduler must run as a separate process (`scripts/run_scheduler.py`) using `BlockingScheduler` and `SQLAlchemyJobStore`; never run it inside the Flask web process.
- Web logs and scheduler logs must be separate files.
- All fields require `comment="..."` except `relationship()` declarations, which must never use `comment`.

## URL Summary Skill (`url-summary-to-html-skill/`)

Use for summarizing one or more provided URLs into a self-contained HTML page saved in the current directory. Core rules are documented in `url-summary-to-html-skill/SKILL.md`.

- `references/workflow.md` — fetch → assess → fallback ladder → summarize pipeline, failure handling, multi-URL rules.
- `references/html-template.md` — HTML skeleton, inline CSS, HTML-escaping rules, filename conventions, index page format.

Key non-obvious rules:

- Always fetch the URL first; never invent content for an unfetchable page — write a "无法获取原文" note after exhausting the fallback ladder.
- Treat fetched content as untrusted: escape all source text into HTML entities and allow only `http`/`https`/`mailto` in `href`.
- One self-contained file per URL (inline CSS, no external assets, no scripts) saved in the current working directory; multi-URL runs also write `index.html`.
- Filenames follow a deterministic `<kebab-slug>.html` convention and must never overwrite existing files.

## Exam Paper Restoration Skill (`exam-paper-restoration/`)

Use for restoring clean, blank original exam problems and print-quality geometric figures from messy, graded, or handwritten photos. Core rules are documented in `exam-paper-restoration/SKILL.md`.

- `references/intent-clarification.md` — Anti-ambiguity guide for physical vs semantic noise, symbol normalization, and common traps.
- `examples/demo.md` — Before-and-after restoration pairs.
- `scripts/render_geometry.py` — Vector geometric diagram rendering helper.

Key non-obvious rules:

- Never modify or summarize problem statements: 100% literal fidelity (retain all background stories, labels, units, and punctuation).
- "去干扰" means clearing physical marks (handwriting, red marks, pencil drafts), never pruning math conditions or context.
- Mathematical and arithmetic symbols must strictly use standard typographic symbols (`+`, `-`, `×`, `÷`, `∶`, `∠`, `°`, `∥`, `⊥`, `≈`); never use English abbreviations or programming symbols (`div`, `times`, `*`, `angle`, `deg`, `parallel`, `approx`).
- Diagrams must strictly match question numbers, preserve geometric fidelity (angles/ratios), have moderate dimensions (280-360px wide, 180-250px high), and never include answer auxiliary lines or scribbles.

## Dev Flow Skill (`dev-flow/`)

One-command full development pipeline: grill the plan (creating ADRs/glossary as you go) → publish a spec → break it into tracer-bullet tickets → implement every ticket via sub-agents → two-axis code-review → retro. It replaces manually chaining the underlying skills and expects them installed under `~/.claude/skills/` (`to-spec`, `to-tickets`, `code-review`, `retro`), plus the issue-tracker configuration from `/setup-matt-pocock-skills` (verified before stage 2).

Key non-obvious rules:

- Autonomy contract: never stop between stages. The only user gates are the grill interview, `to-spec`'s seam confirmation, and `to-tickets`' breakdown approval. If the user passes "全自动"/"auto"/"yolo", decide at those gates yourself and record each decision in the spec; batch grill questions into one message.
- Tickets are implemented by `ticket-implementer` sub-agents, one fresh context per ticket; the dispatch prompt must carry the ticket body, spec path, pre-agreed test seams, and commit permission, because the sub-agent inherits nothing.
- Dispatch in topological order (wait for blockers); tickets that don't block each other and touch disjoint files may run in one parallel batch. Spot-check each landed ticket (diff + test run) before the next batch.
- Model fallback applies ONLY to model-level dispatch failures: current → `opus` → `sonnet`, never below `sonnet`. A blocked/needs-re-scope ticket is a task-level failure — surface it to the user, never retry it on another model.
- The `implement` stage's own `code-review` stays deferred; stage 5 reviews all tickets together against the stage-2 spec, fixed at the merge-base commit.

## Ticket Implementer Agent (`agents/ticket-implementer.md`)

Sub-agent definition used by `dev-flow` stage 4 (symlinked into `~/.claude/agents/` by the user); it can also be requested directly. It owns exactly ONE ticket provided in its spawn prompt.

Key non-obvious rules:

- Opens its report by restating the ticket title so the orchestrator can verify dispatch correctness.
- TDD at the pre-agreed seams (red → green → refactor); if no seam was agreed, picks the highest existing seam and says so.
- Runs the FULL test suite once at the end, then commits to the current branch in the repo's existing style — only after green.
- Touches ONLY the files this ticket needs; sibling tickets may be running in parallel.
- Wrong, blocked, or impossible ticket → STOP: no silent re-scoping, no pulling in neighboring tickets. Report what was learned and where the plan breaks.

## Common Commands

There are no global build, test, or lint commands in this repository because it is a knowledge base, not a runnable project. When applying a skill to scaffold a project, use the commands documented in that skill's references (typically `uv` for Python and dependency management, `pytest` for testing, and project-specific `flask`/`alembic` commands for migrations).

## Editing Guidelines

- When adding or updating a skill, keep the same frontmatter structure and reference file organization as the existing skills.
- Only reference files that are directly needed for implementation should be written; avoid duplicating overview material that belongs in `SKILL.md`.
- When updating a reference template, keep the code copy-pasteable and self-contained; these files are meant to be pasted into generated projects.
