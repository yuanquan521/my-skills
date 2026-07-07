# Responses Reference

Use this reference when implementing unified success responses, error envelopes, paginated lists, or response models.

## Response Shape

All API responses — success and error — share one envelope:

```json
{
  "success": true,
  "code": "OK",
  "message": "ok",
  "data": {},
  "request_id": "optional-request-id"
}
```

Errors use the same shape with `success=false`, an error code (e.g. `VALIDATION_ERROR`, `INTERNAL_SERVER_ERROR`), and `data` carrying optional structured details (validation errors, conflict info, etc.).

## `app/core/responses.py`

```python
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    code: str
    message: str
    data: T | None = None
    request_id: str | None = None


def ok(
    data: T | None = None,
    message: str = "ok",
    request_id: str | None = None,
) -> ApiResponse[T]:
    return ApiResponse(
        success=True,
        code="OK",
        message=message,
        data=data,
        request_id=request_id,
    )


def error(
    code: str,
    message: str,
    *,
    data: object | None = None,
    request_id: str | None = None,
) -> ApiResponse[object]:
    return ApiResponse(
        success=False,
        code=code,
        message=message,
        data=data,
        request_id=request_id,
    )
```

`error(...)` exists so exception handlers do not hand-roll dicts that drift from `ApiResponse`. If `ApiResponse` gains a new field, success and error responses change together.

## Endpoint Pattern

```python
from app.core.responses import ApiResponse, ok
from app.db.session import DbSession
from app.middleware.request_context import RequestId
from app.modules.users.schemas import UserRead
from app.modules.users.service import UserService


async def list_users(
    db: DbSession,
    request_id: RequestId,
) -> ApiResponse[list[UserRead]]:
    users = await UserService(db).list_users()
    return ok(users, request_id=request_id)
```

`RequestId` is the typed dependency from `logging.md`. Endpoints that do not need the request ID can drop the parameter; the middleware still puts the ID on the response header.

## Pagination

For list endpoints, prefer a typed `Page[T]` payload over ad hoc keys. This keeps clients from inventing their own paging shapes per resource.

```python
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)


async def list_users(
    db: DbSession,
    request_id: RequestId,
    limit: int = 50,
    offset: int = 0,
) -> ApiResponse[Page[UserRead]]:
    users, total = await UserService(db).list_users(limit=limit, offset=offset)
    return ok(
        Page(items=users, total=total, limit=limit, offset=offset),
        request_id=request_id,
    )
```

If a project needs cursor-based pagination instead, swap `Page` for a `CursorPage[T]` with `next_cursor` / `prev_cursor`. The envelope stays the same.

## Route response models

Always set `response_model=ApiResponse[...]` on the `RouteSpec` so FastAPI emits the envelope in the OpenAPI schema. See `routing.md`.

## Usage Notes

- Endpoint functions return `ok(data)` for success and raise `AppError` for failures (handled centrally — see `exceptions.md`). They should not return `error(...)` directly; that helper lives in exception handlers.
- Include `request_id` in success envelopes when the project wants response bodies and headers to match.
- Do not return module-specific response wrappers.
- Keep response keys stable because clients may depend on them.
