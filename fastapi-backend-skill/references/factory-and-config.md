# Factory and Configuration Reference

Use this reference when implementing app startup, factory mode, settings, `.env`, or multi-environment configuration.

## Required Files

- `app/main.py`
- `app/factory.py`
- `app/core/config.py`
- `.env.example`

## `app/main.py`

```python
from app.factory import create_app


app = create_app()
```

## `app/factory.py`

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import create_engine, create_sessionmaker
from app.middleware.request_context import RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.sessionmaker = create_sessionmaker(engine)
    try:
        yield
    finally:
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.state.settings = settings

    if settings.trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    if settings.cors_origins:
        allow_credentials = "*" not in settings.cors_origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_router)
    register_exception_handlers(app)

    return app
```

Notes on the factory:

- `lifespan` is the place where things that need a settings-aware lifecycle (engine, background workers, external clients) are created and torn down. Module-level globals do not get this guarantee.
- The CORS guard exists because browsers reject `Access-Control-Allow-Credentials: true` together with `Access-Control-Allow-Origin: *`. See `security.md` for the rationale.

## `app/core/config.py`

```python
import os
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


AppEnv = Literal["local", "development", "test", "staging", "production"]


def env_file_order() -> tuple[str, str]:
    app_env = os.getenv("APP_ENV", "development")
    return (".env", f".env.{app_env}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file_order(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FastAPI Backend"
    app_version: str = "0.1.0"
    app_env: AppEnv = "development"
    debug: bool = False
    log_level: str = "INFO"
    log_json: bool = False
    database_url: str

    cors_origins: list[str] = Field(default_factory=list)
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    secret_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

## `.env.example`

```text
APP_NAME=FastAPI Backend
APP_VERSION=0.1.0
APP_ENV=development
DEBUG=false
LOG_LEVEL=INFO
LOG_JSON=false
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app
CORS_ORIGINS=["http://localhost:3000"]
TRUSTED_HOSTS=["localhost","127.0.0.1"]
SECRET_KEY=change-me
```

## Notes

- Keep configuration access centralized through `Settings`.
- Avoid scattered `os.getenv(...)` calls outside `app/core/config.py` (the one exception is `env_file_order()` which selects which `.env` overlay to load — that has to read the env before `Settings` is constructed).
- For tests, prefer `create_app(test_settings)` plus `app.dependency_overrides[...]` overrides rather than mutating global environment variables in test bodies.
- `get_settings()` is cached. Tests that need fresh settings should construct `Settings(...)` directly and pass it to `create_app`.
