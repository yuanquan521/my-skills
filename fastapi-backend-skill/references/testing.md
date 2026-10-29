# Testing Reference

Use this reference when adding tests for the app factory, configuration loading, route registry, response envelope, exception handling, request IDs, health checks, services, or data access.

## Rules

- Run tests through `uv run pytest`.
- Use the app factory to create test apps; never import a module-level `app` for tests.
- Override dependencies with `app.dependency_overrides` instead of mutating global application state or env vars.
- Keep database tests isolated — either a transactional rollback fixture or schema cleanup between tests.
- Add a static check that no FastAPI route decorators were introduced when refactoring routing.

## Where fixtures live

Fixtures go in `tests/conftest.py` so they are auto-discovered by pytest and shared across test modules.

## `tests/conftest.py`

```python
import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.factory import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_name="Test API",
        app_version="0.1.0",
        app_env="test",
        debug=True,
        database_url=os.getenv(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/test_app",
        ),
    )


@pytest.fixture
def app(test_settings):
    return create_app(test_settings)


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
```

The default `database_url` works locally but must be overridable from CI — read from `TEST_DATABASE_URL` so the same `Settings(...)` call works in both environments.

## Dependency Overrides

The most common test pattern: override `get_db` to inject a test session or mock. `app.dependency_overrides` is keyed by the dependency function, not by its `Depends(...)` wrapper.

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db


class FakeSession: ...  # whatever your tests need


@pytest.fixture
async def client_with_fake_db(app):
    fake = FakeSession()

    async def override_get_db():
        yield fake

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
```

For real-database integration tests, override `get_db` with a session bound to a transactional sessionmaker, or skip the override and let the factory's `lifespan` build a real engine against a dedicated test database.

## Response and Request ID Test

```python
async def test_health_response_envelope(client):
    response = await client.get("/api/v1/health", headers={"x-request-id": "test-id"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-id"
    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["request_id"] == "test-id"
```

## Route Decorator Static Check

```python
from pathlib import Path


def test_no_fastapi_route_decorators():
    forbidden = (
        "@router.get",
        "@router.post",
        "@router.put",
        "@router.patch",
        "@router.delete",
        "@app.get",
        "@app.post",
        "@app.put",
        "@app.patch",
        "@app.delete",
    )
    for path in Path("app").rglob("*.py"):
        text = path.read_text()
        assert not any(marker in text for marker in forbidden), path
```

This is also worth running as a CI lint step so the rule is enforced even when full tests are skipped.

## Database Test Notes

- Prefer a real PostgreSQL test database for data-access tests; SQLite often hides type/cast/constraint differences.
- Use transactions or schema cleanup to isolate tests.
- Service tests may use faked sessions when the behavior under test is business logic rather than SQL.

## Coverage Targets

- `create_app` wires lifespan, router, middleware, handlers, and settings.
- `.env` settings can be overridden for tests via `Settings(...)` directly.
- Route registry exposes expected paths.
- Success and error responses follow the envelope.
- Request IDs are propagated to both the response header and the body.
- Services and data-access paths cover the changed behavior, including rollback paths.
