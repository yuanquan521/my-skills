# Logging Reference

Use this reference when implementing centralized logging, request IDs, or request tracing.

## Rules

- Configure logging once in the app factory.
- Use `get_logger(__name__)` in feature modules.
- Do not call `logging.basicConfig(...)` in feature modules.
- Do not use `print(...)` for application logging.
- Do not log secrets, passwords, tokens, or full database URLs.
- Include request IDs in response headers and error envelopes.

## `app/core/logging.py`

```python
import logging

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
```

`force=True` lets the factory reconfigure logging when tests build several apps with different settings; without it, the second `basicConfig` call is silently a no-op.

## `app/middleware/request_context.py`

This middleware is written as pure ASGI rather than `BaseHTTPMiddleware`. `BaseHTTPMiddleware` buffers response bodies and changes exception-handling timing; for header-only work like request IDs, the pure ASGI form is both faster and avoids those edge cases.

```python
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id: str | None = None
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                request_id = value.decode("latin-1")
                break
        request_id = request_id or str(uuid4())

        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_request_id)
```

The middleware writes to the ASGI `scope["state"]` dictionary. FastAPI wraps that dictionary as `request.state`, so endpoints continue to use `request.state.request_id`.

## Optional: a `RequestId` dependency

To avoid `getattr(request.state, "request_id", None)` repeated in every endpoint, expose a small dependency:

```python
from typing import Annotated

from fastapi import Depends, Request


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


RequestId = Annotated[str | None, Depends(get_request_id)]
```

Endpoints then read it as a typed parameter:

```python
async def list_users(db: DbSession, request_id: RequestId) -> ApiResponse[list[UserRead]]: ...
```

## Factory Registration

```python
from app.core.logging import configure_logging
from app.middleware.request_context import RequestContextMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    app = FastAPI(...)
    app.add_middleware(RequestContextMiddleware)
    return app
```

## Notes

- JSON logging can be added later behind the same `configure_logging(settings)` API; switch on `settings.log_json`.
- Keep request IDs available through `request.state.request_id`.
- Exception handlers should use `get_logger(__name__)` and include the request ID in the unified response. See `exceptions.md`.
