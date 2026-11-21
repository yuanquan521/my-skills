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

`RequestId` is the typed dependency from `logging.md`. Endpoints that do not need the request ID can drop the parameter; the middleware still puts the ID on the response header.

## Pagination

For list endpoints, prefer a typed `Page[T]` payload over ad hoc keys. This keeps clients from inventing their own paging shapes per resource. Every paginated query also needs a deterministic `.order_by(...)` — see the note below the example.

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

Every offset/limit query must apply a deterministic `.order_by(...)` — typically the primary key or a unique timestamp. Without stable ordering, PostgreSQL may return rows in different orders across page fetches, and pagination silently skips or repeats rows.

If a project needs cursor-based pagination instead, swap `Page` for a `CursorPage[T]` with `next_cursor` / `prev_cursor`. The envelope stays the same.

## Route response models

Always set `response_model=ApiResponse[...]` on the `RouteSpec` so FastAPI emits the envelope in the OpenAPI schema. See `routing.md`.

## Time Fields (display-ready UTC+8 strings)

The time pipeline is UTC+8 (`Asia/Shanghai`) end to end: the database stores UTC+8 wall-clock times in naive `DateTime` columns (`now_cn` — see `database.md`), so stored values are exactly what clients see. When the API explicitly requires display-ready times, datetime fields serialize as human-readable `YYYY-MM-DD HH:MM:SS` strings (e.g. `2026-11-09 14:30:00`) — not raw ISO-8601 strings or epoch timestamps. Stored values are already UTC+8, so serialization is pure formatting:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer

from app.core.time import to_cn_time


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return to_cn_time(value)
```

The formatting lives in the schema layer (`field_serializer`), never inside services or ORM models — endpoints keep returning plain `ApiResponse[...]` envelopes.

## Usage Notes

- Endpoint functions return `ok(data)` for success and raise `AppError` for failures (handled centrally — see `exceptions.md`). They should not return `error(...)` directly; that helper lives in exception handlers.
- Include `request_id` in success envelopes when the project wants response bodies and headers to match.
- Do not return module-specific response wrappers.
- Keep response keys stable because clients may depend on them.
