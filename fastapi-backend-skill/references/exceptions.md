# Exceptions Reference

Use this reference when implementing application errors, validation errors, or global exception handlers.

## `app/core/exceptions.py`

```python
from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)
```

## `app/core/exception_handlers.py`

```python
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.core.responses import error


logger = get_logger(__name__)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error(
            code=exc.code,
            message=exc.message,
            data=exc.details,
            request_id=_request_id(request),
        ).model_dump(),
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            data=exc.errors(),
            request_id=_request_id(request),
        ).model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error(
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error",
            data=None,
            request_id=_request_id(request),
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
```

Going through `error(...)` (from `responses.py`) means error envelopes always match `ApiResponse`. Adding a field to the envelope changes both success and error paths together; hand-rolled dicts here would silently drift.

## Usage Notes

- Services should raise `AppError` or domain-specific subclasses such as `class NotFoundError(AppError): ...` with a sensible default `code` and `status_code`.
- Avoid constructing scattered `HTTPException` instances inside services — that bypasses the unified envelope and forces clients to handle two response shapes.
- Repositories should not raise `AppError`. Surface low-level errors as plain exceptions; let the service translate them into a domain error with the right code.
- Keep error codes stable because clients may depend on them.
- Exception handlers always include the request ID in the envelope so an error report can be cross-referenced with logs.
