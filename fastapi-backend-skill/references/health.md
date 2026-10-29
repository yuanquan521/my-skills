# Health Reference

Use this reference when implementing health, readiness, dependency checks, or smoke-test endpoints.

## Rules

- Health and readiness have different meanings, and conflating them breaks deployments.
- `/health` proves the application process is alive and responsive. It must not require PostgreSQL — if the DB is down, the orchestrator should still see the process as alive so it does not kill and restart pods that are otherwise fine.
- `/ready` proves required dependencies such as PostgreSQL are reachable. Load balancers gate traffic on `/ready`, not `/health`.
- Both endpoints use centralized route registration and the unified response envelope.

## Single-File Domain

Health is a thin domain, so it stays a single module: `app/api/v1/health.py` holds schemas, endpoint functions, and the `routes` list.

```python
# app/api/v1/health.py
from pydantic import BaseModel
from sqlalchemy import text

from app.api.dependencies import DbSession, RequestId
from app.api.route_registry import RouteSpec
from app.core.responses import ApiResponse, ok


class HealthStatus(BaseModel):
    status: str


async def health(request_id: RequestId) -> ApiResponse[HealthStatus]:
    return ok(HealthStatus(status="ok"), request_id=request_id)


async def ready(db: DbSession, request_id: RequestId) -> ApiResponse[HealthStatus]:
    await db.execute(text("select 1"))
    return ok(HealthStatus(status="ready"), request_id=request_id)


routes = [
    RouteSpec(
        path="/health",
        endpoint=health,
        methods=["GET"],
        response_model=ApiResponse[HealthStatus],
        name="health",
        tags=["health"],
    ),
    RouteSpec(
        path="/ready",
        endpoint=ready,
        methods=["GET"],
        response_model=ApiResponse[HealthStatus],
        name="ready",
        tags=["health"],
    ),
]
```

## Test Notes

- Test `/health` without requiring a database — assert it returns 200 even if `get_db` would fail.
- Test `/ready` with a database override or mocked session.
- Keep these endpoints small because they are used by deployment systems and run on every probe interval.
