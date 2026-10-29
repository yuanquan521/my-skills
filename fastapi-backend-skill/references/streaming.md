# Streaming Reference

Use this reference when adding streaming endpoints: Server-Sent Events (SSE), JSON Lines, or byte/file streams.

## Rules

- Streaming endpoints are the **sole documented exception** to the `ApiResponse` envelope — a stream cannot be wrapped without defeating it. Everything else (auth, registration, request-ID header) follows the normal contract.
- Declare the response class on the `RouteSpec` (`response_class=...`), never by returning a response object from an `async def` endpoint — route metadata stays in the domain's `routes` list.
- Streaming endpoints are `async` generators: declare `AsyncIterable[T]` return types and `yield`.
- Auth applies unchanged: `CurrentUser` parameter or `RouteSpec.dependencies`.
- The request-ID middleware still sets the response header; there is no body envelope, so no `request_id` field.
- `response_model` (envelope routes) and `response_class` (stream routes) are mutually exclusive per route.

## `RouteSpec.response_class`

`app/api/route_registry.py` carries the field and passes it through to `add_api_route`:

```python
@dataclass(frozen=True)
class RouteSpec:
    ...
    response_class: type | None = None


def register_routes(router: APIRouter, routes: list[RouteSpec]) -> None:
    for route in routes:
        router.add_api_route(
            ...,
            response_model=route.response_model,
            response_class=route.response_class,
        )
```

## Server-Sent Events (SSE)

```python
# app/api/v1/events.py  (single-file domain)
from collections.abc import AsyncIterable

from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.route_registry import RouteSpec


async def stream_progress() -> AsyncIterable[ServerSentEvent]:
    async for step in watch_progress():
        yield ServerSentEvent(data={"step": step}, event="progress")


routes = [
    RouteSpec(
        path="/events/progress",
        endpoint=stream_progress,
        methods=["GET"],
        response_class=EventSourceResponse,
        name="stream_progress",
        tags=["events"],
    ),
]
```

Plain objects are JSON-serialized as `data:` fields automatically. Yield Pydantic models (`AsyncIterable[OrderRead]`) for typed payloads — Pydantic does the serialization; use `ServerSentEvent` only when you need its extra fields (`event`, `id`, `retry`, `comment`), and `raw_data` for pre-formatted strings.

## JSON Lines

```python
async def stream_orders() -> AsyncIterable[OrderRead]:
    async for order in iterate_orders():
        yield order


routes = [
    RouteSpec(
        path="/orders/stream",
        endpoint=stream_orders,
        methods=["GET"],
        name="stream_orders",
        tags=["orders"],
    ),
]
```

No `response_class` needed — the declared `AsyncIterable[OrderRead]` return type drives JSON Lines serialization.

## Bytes and files

Pin the media type with a `StreamingResponse` subclass declared on the `RouteSpec`; use a plain `def` generator for blocking file reads so it runs in the threadpool (see the blocking-calls pitfall in `SKILL.md`):

```python
from fastapi.responses import StreamingResponse


class PNGStreamingResponse(StreamingResponse):
    media_type = "image/png"


def stream_avatar(avatar_id):
    with open(avatar_path(avatar_id), "rb") as f:
        yield from f


routes = [
    RouteSpec(
        path="/avatars/{avatar_id}",
        endpoint=stream_avatar,
        methods=["GET"],
        response_class=PNGStreamingResponse,
        name="stream_avatar",
        tags=["avatars"],
    ),
]
```

## Notes

- Long-lived streams hold whatever they capture. If the generator accepted `DbSession`, the session stays open for the whole stream — prefer materializing the row IDs first, then streaming from an iterator that owns no session, or open short-lived sessions per chunk.
- Background producers (queues, pub/sub) pair naturally with SSE: the endpoint awaits the queue and yields events; shutdown logic belongs in the producing task, not the generator.

## Testing

```python
async def test_sse_stream(client):
    async with client.stream("GET", "/api/v1/events/progress") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        lines = [line async for line in response.aiter_lines()]
    assert any(line.startswith("event:progress") for line in lines)
```

Assert on raw lines/chunks, not the envelope — there is none.
