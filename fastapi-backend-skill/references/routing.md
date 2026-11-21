# Centralized Routing Reference

Use this reference when implementing route registration, adding modules, or refactoring decorator-based FastAPI routes.

## Rule

Do not use FastAPI route decorators such as `@router.get`, `@router.post`, or `@app.get`. Register routes explicitly with `add_api_route` through a central route registry. The reason is auditability: when every route flows through one registry, "what does this API expose?" is answerable by reading one file, and refactors that touch route metadata (auth dependencies, deprecations, versioning) happen in one place rather than scattered decorators.

## `app/api/route_registry.py`

```python
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, params
from fastapi.responses import JSONResponse


@dataclass(frozen=True)
class RouteSpec:
    path: str
    endpoint: Callable[..., Any]
    methods: list[str]
    name: str | None = None
    response_model: Any | None = None
    response_class: type = JSONResponse
    status_code: int | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    dependencies: Sequence[params.Depends] | None = None
    include_in_schema: bool = True
    deprecated: bool = False


def register_routes(router: APIRouter, routes: list[RouteSpec]) -> None:
    for route in routes:
        router.add_api_route(
            route.path,
            route.endpoint,
            methods=route.methods,
            name=route.name,
            response_model=route.response_model,
            response_class=route.response_class,
            status_code=route.status_code,
            summary=route.summary,
            description=route.description,
            tags=route.tags,
            dependencies=list(route.dependencies) if route.dependencies else None,
            include_in_schema=route.include_in_schema,
            deprecated=route.deprecated,
        )
```

The extra fields cover the common reasons people reach for decorators: dependency injection (`Depends(require_admin)`), hiding internal endpoints (`include_in_schema=False`), signaling deprecation, and streaming (`response_class` for SSE/JSON Lines/bytes — see `streaming.md`; stream routes are the only envelope exception). Adding them to `RouteSpec` keeps everything in `routes.py` instead of leaking back into `endpoints.py`.

## Module Endpoint

```python
from app.api.dependencies import DbSession, RequestId
from app.api.v1.users.schemas import UserRead
from app.api.v1.users.service import UserService
from app.core.responses import ApiResponse, ok


async def list_users(
    db: DbSession,
    request_id: RequestId,
) -> ApiResponse[list[UserRead]]:
    users = await UserService(db).list_users()
    return ok(users, request_id=request_id)
```

## Module Routes

Always set `response_model=ApiResponse[...]`. Without it, FastAPI's OpenAPI schema describes the endpoint return type instead of the envelope, and clients lose sight of `success` / `code` / `request_id`.

```python
from app.api.route_registry import RouteSpec
from app.core.responses import ApiResponse
from app.api.v1.users import endpoints
from app.api.v1.users.schemas import UserRead


routes = [
    RouteSpec(
        path="/users",
        endpoint=endpoints.list_users,
        methods=["GET"],
        response_model=ApiResponse[list[UserRead]],
        name="list_users",
        tags=["users"],
    ),
]
```

## Central API Router

```python
from fastapi import APIRouter

from app.api.route_registry import register_routes
from app.api.v1.health import routes as health_routes         # single-file domain
from app.api.v1.users.routes import routes as user_routes     # domain package


api_router = APIRouter(prefix="/api/v1")

register_routes(api_router, health_routes)
register_routes(api_router, user_routes)
```

Adding a new domain is a two-step change: create `app/api/v1/<domain>.py` with schemas, endpoints, and its `routes` list (promote to a package later if growth triggers fire), then import and register the routes from `app/api/router.py`. Both forms import identically. Treat this central file as the API surface manifest.

## Versioning

When `/api/v2` is needed, add an `app/api/v2/` package with its own domain packages and register its routes from the central manifest (`app/api/router.py`). Do not version inside individual `routes.py` modules — that re-fragments the registry.

## Migration Notes

- Move decorated endpoint functions into the domain module (`<domain>.py`, or `endpoints.py` in package form).
- Move path, method, tags, status code, response model, dependencies, and visibility flags into `routes.py`.
- Import each module route list once from the central API router.
- The static decorator check in `testing.md` will fail the build if a stray decorator slips back in.
