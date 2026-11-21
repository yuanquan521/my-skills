---
name: fastapi-backend-skill
description: Establishes a fixed FastAPI backend project structure with uv, `app/factory.py` create_app + lifespan, `.env`-driven settings, PostgreSQL via SQLAlchemy with explicit transactions, centralized route registration without `@router` decorators, unified `ApiResponse` envelope, global exception handlers, single-source logging with ASGI request-ID middleware, separate health/readiness endpoints, pytest conventions, and a security baseline. Use whenever creating, refactoring, reviewing, or extending a FastAPI + PostgreSQL backend, or mentioning `create_app`, "工厂模式", "统一路由管理", "统一返回", "统一异常处理", "统一日志", "不要装饰器", "固定代码结构", `uv`, Alembic, or "route registry" in a FastAPI context. Always invoke before generating FastAPI scaffolding so the project conforms to this structure.
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
- For creating a new domain — single-file or package, with schemas, models, endpoints, routes, and growth tiers — read `references/module-template.md`.
- For unified response envelope, error helper, and pagination, read `references/responses.md`.
- For application errors and global exception handling, read `references/exceptions.md`.
- For centralized logging, request IDs, and ASGI middleware, read `references/logging.md`.
- For health and readiness endpoints, read `references/health.md`.
- For pytest, app factory tests, dependency overrides, and route checks, read `references/testing.md`.
- For CORS, trusted hosts, secrets, password handling, and logging redaction, read `references/security.md`.
- For JWT/OAuth2 authentication, token issuance, password hashing modules, and `CurrentUser` route protection, read `references/authentication.md`.
- For SSE, JSON Lines, byte streams, and `RouteSpec.response_class`, read `references/streaming.md`.

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
- `app/api/dependencies.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/core/exception_handlers.py`
- `app/core/security.py` (password hashing and JWT helpers; no FastAPI imports — present when authentication is)
- `app/core/logging.py`
- `app/core/responses.py`
- `app/core/time.py` (`UTC_PLUS_8`, `now_cn`, `to_cn_time` — shared UTC+8 clock helpers)
- `app/db/base.py`
- `app/db/session.py`
- `app/middleware/request_context.py`
- `app/api/v1/health.py`
- `app/api/v1/<domain>.py` (single-file domain — the default starting form)
- `app/api/v1/<domain>/endpoints.py` (package form, after growth triggers)
- `app/api/v1/<domain>/routes.py`
- `app/api/v1/<domain>/schemas.py`
- `app/api/v1/<domain>/service.py` (complex domains only)
- `app/models/__init__.py` (re-exports every ORM model; imported once by `app/db/base.py`)
- `app/models/<domain>.py` (SQLAlchemy ORM models, one file per domain)
- `.env.example`
- `.python-version`
- `pyproject.toml`
- `uv.lock`
- `alembic.ini`
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

Use one response envelope across the API for both success and error paths. Error envelopes go through the shared `error(...)` helper so they cannot drift from `ApiResponse`. Streaming routes (`RouteSpec.response_class`) are the sole exception; see `references/streaming.md`.

The whole time pipeline is UTC+8 (`Asia/Shanghai`): the database stores UTC+8 wall-clock times in naive `DateTime` columns (see `references/database.md`), and when an API explicitly requires display-ready times, datetime fields serialize as human-readable `YYYY-MM-DD HH:MM:SS` strings (e.g. `2026-11-09 14:30:00`) — not raw ISO-8601 strings or epoch timestamps. Storage and API output share one clock: what is stored is what clients see. See `references/responses.md`.

Use typed application exceptions and globally registered exception handlers. Services may raise application errors; repositories should not import FastAPI.

Use one logging module for the whole backend. Configure logging once in the app factory, propagate request IDs through ASGI middleware, and avoid `print` for application logs.

Expose health and readiness endpoints with different meanings: health proves the app process is alive (no DB required), readiness proves required dependencies such as PostgreSQL are reachable.

Keep the security baseline centralized: secrets in environment configuration, CORS and trusted hosts in settings (with the `allow_credentials` guard for `*` origins), no sensitive values in logs, and password handling through hashing when authentication is present.

## Module Boundaries

Use these boundaries consistently:

- Domains live under `app/api/v1/` — start as `<domain>.py` single files and promote to `<domain>/` packages on growth triggers (see `references/module-template.md`)
- `routes` list of `RouteSpec` entries: route metadata only, the sole way endpoints get declared
- `endpoints.py`: FastAPI-facing functions, dependency parameters (package form)
- `schemas.py`: Pydantic request and response models
- `app/models/<domain>.py`: SQLAlchemy ORM models — centralized in the shared models folder, one file per domain, re-exported from `app/models/__init__.py`
- `app/api/dependencies.py`: shared `Annotated` dependency aliases (`DbSession`, `RequestId`, future auth deps); endpoint files import dependencies only from here
- `service.py`: business rules, orchestration, and transaction ownership — added only when a domain has reusable logic
- `repository.py`: not part of the contract; only by explicit project choice, and then no `commit()` and no FastAPI imports
- `app/core/responses.py`: shared `ApiResponse`, `ok(...)`, `error(...)` helpers
- `app/core/exceptions.py`: shared application exceptions
- `app/core/exception_handlers.py`: exception-to-response handlers (`AppError`, `RequestValidationError`, `StarletteHTTPException`, and fallback `Exception`, all via `error(...)`)
- `app/core/logging.py`: logging setup and logger access
- `app/core/time.py`: shared UTC+8 helpers (`UTC_PLUS_8`, `now_cn`, `to_cn_time`)
- `app/middleware/request_context.py`: pure ASGI request ID propagation

Endpoint functions should stay thin. They should handle HTTP-level dependency wiring and call services. Services should not know about route registration. Repositories should not import FastAPI objects.

## Implementation Workflow

1. Inspect the existing project before editing. Record any decisions already made (async/sync, transaction owner, paging shape) and preserve compatible local patterns while enforcing the core rules above.
2. If scaffolding a new backend, create the fixed structure first, then add uv project metadata, the app factory with lifespan, settings, database (engine constructed inside lifespan), route registry, unified responses (`ok` + `error`), exception handlers, logging with ASGI request-context middleware, the health module (`app/api/v1/health.py`), and requested domains under `app/api/v1/`, starting single-file.
3. If refactoring an existing backend, migrate one concern at a time: factory/config, routes, responses (success + error), exceptions, logging, then domain modules.
4. Configure PostgreSQL through centralized settings loaded from `.env`.
5. Choose and document the database transaction boundary before adding services (or an explicitly chosen repository layer).
6. Support environment overlays with consistent variable names, selected by the configured app environment.
7. Manage dependencies and verification commands through uv.
8. Register all routes through the central route registry. Use `RouteSpec.dependencies` instead of decorator-based `Depends`.
9. Add Alembic configuration and a migration whenever models are introduced.
10. Add health and readiness endpoints with the correct semantics (health independent of DB; ready checks DB).
11. Apply the security baseline for configuration, logging, and middleware. Apply the CORS `allow_credentials` guard.
12. Add focused tests for the app factory, configuration loading, route registration, response envelope, exception handling, request ID behavior, health/readiness checks, and touched service behavior (when present). Use `app.dependency_overrides` rather than env mutation.
13. Run the project test and lint commands through uv when available.

## Common Pitfalls

These keep slipping into FastAPI projects. Catch them in review before they ship.

- **Module-level `engine = create_async_engine(...)`.** Tests passing a different `Settings` to `create_app` will silently use the production database. Build the engine inside `lifespan`.
- **`BaseHTTPMiddleware` for request-context work.** It buffers responses and changes exception timing. Use a pure ASGI class that mutates `scope["state"]` and the response headers.
- **Hand-rolled error JSON or missing `StarletteHTTPException` handler.** Hand-rolled dicts drift from `ApiResponse`, and without a `StarletteHTTPException` handler, 404/405 responses and FastAPI's `OAuth2PasswordBearer` 401 bypass the envelope and return `{"detail": "..."}`. Always route every error handler through `error(...)`.
- **Reading `get_settings()` inside `security.py` or feature code.** Bypasses `create_app(test_settings)` isolation. Pass settings (or explicit `secret_key`) from `request.app.state.settings`.
- **`print(...)` in feature modules.** Bypasses log levels and structured logging. Use `get_logger(__name__)`.
- **`HTTPException` raised inside services.** Couples services to FastAPI and skips typed domain codes. Raise `AppError` and let the global handler format the response.
- **Blocking calls inside `async def` endpoints.** Freezes the event loop and tanks every concurrent request. Use `def` endpoints (run in a threadpool) for blocking libraries, or async libraries throughout.
- **`...` ellipsis defaults and `RootModel`.** Required fields need no `...`; validated collections are `Annotated[list[T], Field(...)]` type annotations (FastAPI builds a `TypeAdapter`), not wrapper models. Official FastAPI skill convention.
- **Select-then-insert uniqueness checks.** Race-prone (TOCTOU): two requests can both pass the pre-check. Enforce a unique DB index and translate `IntegrityError` into an `AppError`; keep pre-checks only for friendly early errors.
- **Symmetry layers for thin CRUD domains.** Creating `service.py`/`repository.py` per domain regardless of logic thickness. Add layers for reuse or transaction orchestration, not symmetry.
- **`httpx.AsyncClient(transport=ASGITransport(app=app))` without entering `lifespan`.** `ASGITransport` does not invoke ASGI `lifespan`, so `app.state.sessionmaker` stays unset in integration tests unless wrapped in `app.router.lifespan_context(app)` or overridden via `app.dependency_overrides`.
- **`app.dependency_overrides` not cleared after a test.** Leaks into the next test. Wrap overrides in a fixture's `try/finally`.
- **`os.getenv(...)` outside `app/core/config.py`.** Bypasses the typed `Settings` model and makes overrides invisible.
- **`Base.metadata.create_all(engine)` at startup in production code.** Skips Alembic's history. Run migrations explicitly.
- **Route decorators (`@router.get`, `@app.post`) re-introduced under deadline.** Run the static check from `testing.md` in CI so this fails the build, not the next reviewer.
- **`allow_credentials=True` with `allow_origins=["*"]`.** Browsers reject the response. The factory guard derives the credentials flag from the origins list.
- **Health endpoint touching the database.** Orchestrators kill the pod when DB is briefly down, even though the process is fine. Keep `/health` independent of `/ready`.

## Review Checklist

Before finishing, verify the items touched by your change:

- [ ] **Assembly & config**: `app/main.py` only exposes `app = create_app()`; engine/sessionmaker live in `lifespan`; `.env` + `Settings` centralize config with `pyproject.toml`/`uv.lock`/`.python-version` managed by `uv`.
- [ ] **Routing & domains**: zero `@router.*`/`@app.*` decorators (verified by static test); routes visible from `app/api/router.py`; thin CRUD stays single-file; ORM models live in `app/models/` and are re-exported for Alembic.
- [ ] **Envelope & errors**: success uses `ok(...)`; all error handlers (`AppError`, `RequestValidationError`, `StarletteHTTPException`, `Exception`) use `error(...)`.
- [ ] **Observability & probes**: single logging module (`get_logger`, no `print`); pure ASGI `RequestContextMiddleware` sets header + envelope `request_id`; `/health` skips DB while `/ready` checks PostgreSQL.
- [ ] **Security & tests**: CORS `allow_credentials` guard, no secrets in code/logs, explicit `secret_key` passed into JWT helpers; tests use `create_app(test_settings)` + `app.dependency_overrides` (and `lifespan_context` when hitting real DB).

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
