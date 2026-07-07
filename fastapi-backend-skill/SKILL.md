---
name: fastapi-backend-structure
description: Establishes a fixed FastAPI backend project structure with uv-based Python and dependency management, an `app/factory.py` create_app pattern, `.env`-driven settings, PostgreSQL via SQLAlchemy with explicit transaction boundaries, centralized route registration without `@router` decorators, a unified `ApiResponse` envelope for success and errors, global exception handlers, single-source logging with request-ID middleware, separate health/readiness endpoints, opinionated pytest conventions, and a security baseline. Use this skill whenever the user is creating, refactoring, reviewing, or extending a FastAPI + PostgreSQL backend, or mentions any of `app factory`, `create_app`, "工厂模式", "统一路由管理", "统一返回", "统一异常处理", "统一日志", "健康检查", "测试规范", "安全基线", "不要装饰器", "固定代码结构", `uv`, `pyproject.toml`, `uv.lock`, Alembic, or "route registry". Always invoke this skill before generating any FastAPI scaffolding so the project comes out conforming to the same fixed structure.
---

# FastAPI Backend Structure

Use this skill to keep FastAPI backend projects predictable. The backend contract is:

- fixed project structure
- uv-based Python and dependency version management
- FastAPI app factory pattern with `lifespan` for owned resources
- centralized `.env`-based configuration
- PostgreSQL persistence
- explicit database transaction boundaries
- centralized route registration without route decorators
- unified success and error response envelope
- unified exception handling
- unified logging and request tracing
- health/readiness checks
- focused backend testing conventions
- basic security baseline

Keep this `SKILL.md` as the operating guide. Load reference files only when the current task needs their implementation details.

## Progressive Disclosure

Read only the reference files needed for the immediate task:

- For app startup, factory mode, lifespan, and multi-environment settings, read `references/factory-and-config.md`.
- For Python version, dependency, lockfile, and command management with uv, read `references/uv.md`.
- For PostgreSQL, SQLAlchemy, sessions, transactions, and Alembic structure, read `references/database.md`.
- For Alembic async configuration, migration commands, and migration naming rules, read `references/alembic.md`.
- For centralized route registration without decorators, read `references/routing.md`.
- For creating a new domain module with schemas, model, repository, service, endpoints, and routes, read `references/module-template.md`.
- For unified response envelope, error helper, and pagination, read `references/responses.md`.
- For application errors and global exception handling, read `references/exceptions.md`.
- For centralized logging, request IDs, and ASGI middleware, read `references/logging.md`.
- For health and readiness endpoints, read `references/health.md`.
- For pytest, app factory tests, dependency overrides, and route checks, read `references/testing.md`.
- For CORS, trusted hosts, secrets, password handling, and logging redaction, read `references/security.md`.

When scaffolding a brand-new backend, read all reference files once, then implement the smallest complete skeleton that satisfies the user request. When adding one module to an existing backend, read only the references that touch the changed area plus any local project files needed to preserve existing conventions.

## Decisions to Make Early

Before writing code, settle these once and stick to them across the project. Re-deciding mid-implementation is the single biggest source of inconsistency in FastAPI projects.

- **Async vs sync.** Default new projects to async (`AsyncSession`, `asyncpg`). If the existing project is already synchronous SQLAlchemy with PostgreSQL, keep it synchronous unless the user asks for an async migration. Do not mix the two — the engine, sessionmaker, dependency, and tests all change together.
- **Transaction ownership.** Default to service-owned transactions (services decide when to commit; repositories never call `commit()`). Document the choice next to the transaction helper.
- **Request ID propagation.** Default to including `request_id` in both response headers and response bodies. If the project chooses headers-only, document it and apply the rule consistently to error envelopes too.
- **Pagination shape.** Default to `Page[T]` with `items / total / limit / offset`. If the project needs cursor pagination, swap `Page` for `CursorPage` and apply it to all list endpoints — do not let two paging shapes coexist.

## Target Project Layout

For new projects, converge on this layout:

- `app/main.py`
- `app/factory.py`
- `app/api/router.py`
- `app/api/route_registry.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/core/exception_handlers.py`
- `app/core/errors.py`
- `app/core/logging.py`
- `app/core/responses.py`
- `app/db/base.py`
- `app/db/session.py`
- `app/db/migrations.py`
- `app/middleware/request_context.py`
- `app/modules/health/endpoints.py`
- `app/modules/health/routes.py`
- `app/modules/health/schemas.py`
- `app/modules/<domain>/endpoints.py`
- `app/modules/<domain>/routes.py`
- `app/modules/<domain>/schemas.py`
- `app/modules/<domain>/models.py`
- `app/modules/<domain>/repository.py`
- `app/modules/<domain>/service.py`
- `.env.example`
- `.python-version`
- `pyproject.toml`
- `uv.lock`
- `alembic/env.py`
- `alembic/versions/`
- `tests/conftest.py`
- `tests/`

Preserve an existing project's naming only when it already expresses the same boundaries. Do not introduce a second architecture beside an existing compatible one.

## Core Rules

Keep `app/main.py` tiny. It should expose the ASGI app created by `create_app`. App construction belongs in `app/factory.py`.

Use `uv` for Python version selection, dependency management, lockfile management, and project command execution. Do not introduce parallel dependency files unless the existing project requires them for compatibility.

Use `.env` as the canonical configuration interface. Environment-specific differences should be expressed by `.env` overlays or injected settings, not hardcoded Python branches scattered through the codebase.

Use PostgreSQL for persistence. Do not introduce SQLite, in-memory stores, or JSON files for application data unless the user explicitly asks for a disposable prototype.

Construct database engines inside `lifespan`, not at module import. The factory pattern only holds if engine, sessionmaker, and similar settings-bound resources are created when `create_app(settings)` runs. See `references/database.md`.

Make database transaction ownership explicit. Do not leave commit and rollback behavior to chance.

Use Alembic for every schema change. Do not create or mutate tables from application startup code.

Use explicit route registration through a central registry. Do not add FastAPI route decorators in endpoint modules or app startup files.

Use one response envelope across the API for both success and error paths. Error envelopes go through the shared `error(...)` helper so they cannot drift from `ApiResponse`.

Use typed application exceptions and globally registered exception handlers. Services may raise application errors; repositories should not import FastAPI.

Use one logging module for the whole backend. Configure logging once in the app factory, propagate request IDs through ASGI middleware, and avoid `print` for application logs.

Expose health and readiness endpoints with different meanings: health proves the app process is alive (no DB required), readiness proves required dependencies such as PostgreSQL are reachable.

Keep the security baseline centralized: secrets in environment configuration, CORS and trusted hosts in settings (with the `allow_credentials` guard for `*` origins), no sensitive values in logs, and password handling through hashing when authentication is present.

## Module Boundaries

Use these boundaries consistently:

- `endpoints.py`: FastAPI-facing functions, dependency parameters, request/response schemas
- `schemas.py`: Pydantic request and response models
- `models.py`: SQLAlchemy ORM models
- `repository.py`: database queries and persistence methods
- `service.py`: business rules and orchestration
- `routes.py`: route metadata only
- `app/core/responses.py`: shared `ApiResponse`, `ok(...)`, `error(...)` helpers
- `app/core/exceptions.py`: shared application exceptions
- `app/core/exception_handlers.py`: exception-to-response handlers (use `error(...)` from responses)
- `app/core/logging.py`: logging setup and logger access
- `app/middleware/request_context.py`: pure ASGI request ID propagation

Endpoint functions should stay thin. They should handle HTTP-level dependency wiring and call services. Services should not know about route registration. Repositories should not import FastAPI objects.

## Implementation Workflow

1. Inspect the existing project before editing. Record any decisions already made (async/sync, transaction owner, paging shape) and preserve compatible local patterns while enforcing the core rules above.
2. If scaffolding a new backend, create the fixed structure first, then add uv project metadata, the app factory with lifespan, settings, database (engine constructed inside lifespan), route registry, unified responses (`ok` + `error`), exception handlers, logging with ASGI request-context middleware, the health module, and requested domain modules.
3. If refactoring an existing backend, migrate one concern at a time: factory/config, routes, responses (success + error), exceptions, logging, then domain modules.
4. Configure PostgreSQL through centralized settings loaded from `.env`.
5. Choose and document the database transaction boundary before adding repositories or services.
6. Support environment overlays with consistent variable names, selected by the configured app environment.
7. Manage dependencies and verification commands through uv.
8. Register all routes through the central route registry. Use `RouteSpec.dependencies` instead of decorator-based `Depends`.
9. Add Alembic configuration and a migration whenever models are introduced.
10. Add health and readiness endpoints with the correct semantics (health independent of DB; ready checks DB).
11. Apply the security baseline for configuration, logging, and middleware. Apply the CORS `allow_credentials` guard.
12. Add focused tests for the app factory, configuration loading, route registration, response envelope, exception handling, request ID behavior, health/readiness checks, and touched service/repository behavior. Use `app.dependency_overrides` rather than env mutation.
13. Run the project test and lint commands through uv when available.

## Common Pitfalls

These keep slipping into FastAPI projects. Catch them in review before they ship.

- **Module-level `engine = create_async_engine(...)`.** Tests passing a different `Settings` to `create_app` will silently use the production database. Build the engine inside `lifespan`.
- **`BaseHTTPMiddleware` for request-context work.** It buffers responses and changes exception timing. Use a pure ASGI class that mutates `scope["state"]` and the response headers.
- **Hand-rolled error JSON in exception handlers.** Drifts from `ApiResponse` over time. Always go through the `error(...)` helper.
- **`print(...)` in feature modules.** Bypasses log levels and structured logging. Use `get_logger(__name__)`.
- **`HTTPException` raised inside services.** Couples services to FastAPI and skips the unified envelope. Raise `AppError` and let the global handler format the response.
- **`from fastapi import ...` inside `repository.py`.** Repositories should be importable from CLI scripts and migrations without dragging the web framework in.
- **`app.dependency_overrides` not cleared after a test.** Leaks into the next test. Wrap overrides in a fixture's `try/finally`.
- **`os.getenv(...)` outside `app/core/config.py`.** Bypasses the typed `Settings` model and makes overrides invisible.
- **`Base.metadata.create_all(engine)` at startup in production code.** Skips Alembic's history. Run migrations explicitly.
- **Route decorators (`@router.get`, `@app.post`) re-introduced under deadline.** Run the static check from `testing.md` in CI so this fails the build, not the next reviewer.
- **`allow_credentials=True` with `allow_origins=["*"]`.** Browsers reject the response. The factory guard derives the credentials flag from the origins list.
- **Health endpoint touching the database.** Orchestrators kill the pod when DB is briefly down, even though the process is fine. Keep `/health` independent of `/ready`.

## Review Checklist

Before finishing, verify:

- No FastAPI route decorators were added.
- Python version and dependencies are managed by uv.
- `pyproject.toml`, `uv.lock`, and `.python-version` are present for new projects.
- App creation goes through `create_app`.
- `app/main.py` only exposes the ASGI app.
- The factory uses `lifespan` to create the engine and sessionmaker; no module-level engine.
- Runtime configuration is centralized in `app/core/config.py` and loaded from `.env` files.
- Different environments use the same configuration keys and differ only by `.env` overlays or injected settings.
- PostgreSQL is the configured database.
- Database transaction ownership is explicit and tested where behavior is nontrivial.
- New ORM models are discoverable by Alembic metadata.
- Schema changes have Alembic migrations; startup code does not call metadata `create_all`.
- All API routes are visible from the central API router or project equivalent.
- Successful API responses use the shared envelope; error responses go through the shared `error(...)` helper.
- Exception handlers are registered through a central function.
- Logging is configured once through the shared logging module.
- Feature modules use named loggers rather than `print`.
- Request IDs are propagated into response headers and error envelopes via pure ASGI middleware.
- Health and readiness endpoints are registered and have separate behavior.
- Tests cover shared infrastructure and the module behavior touched by the change.
- Tests use `app.dependency_overrides` rather than env mutation.
- CORS, trusted hosts (with `allow_credentials` guard), secrets, password handling, and log redaction follow the security baseline when relevant.
- Endpoint functions are thin and do not contain raw SQL or heavy business logic.
- Repository methods do not import FastAPI objects.
- Tests or runnable verification steps cover the changed route paths and shared infrastructure.

## Final Response

When reporting work back to the user, mention only the items relevant to what changed. For a small change, this might be one or two lines. For a from-scratch scaffold, cover the full list:

- files changed or created
- uv version/dependency management status
- app factory and `.env` configuration pattern used
- PostgreSQL/Alembic setup status
- centralized route registration pattern used
- unified response (`ok`/`error`) and exception handling pattern used
- centralized logging and request ID pattern used
- health/readiness, testing, and security baseline status when relevant
- tests or checks run, including any that could not be run

Keep the response concise and practical.
