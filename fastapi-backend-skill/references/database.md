# Database Reference

Use this reference when implementing PostgreSQL, SQLAlchemy sessions, ORM base metadata, or Alembic integration.

## Recommended Stack

- PostgreSQL
- SQLAlchemy 2.x ORM
- `asyncpg` with `postgresql+asyncpg://...`
- Alembic migrations
- request-scoped `AsyncSession`

If the existing project is already synchronous SQLAlchemy with PostgreSQL, keep it synchronous unless the user asks for an async migration. The same factory-owned engine pattern below applies — only the engine type and session class change.

## Why the engine lives on the app, not at module top level

Do not write `engine = create_async_engine(...)` at module import time. The factory pattern only works if the engine is constructed when `create_app(settings)` runs, otherwise tests that pass a different `Settings` get the production database while `app.state.settings` shows the test database — a real source of cross-environment bugs.

The pattern below puts engine construction inside the FastAPI `lifespan` so:

- a fresh engine is created per app instance,
- the engine is disposed cleanly on shutdown,
- `get_db` looks the sessionmaker up from `request.app.state`, never module globals.

## `app/db/session.py`

```python
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
```

## Lifespan Wiring (in `app/factory.py`)

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings
from app.db.session import create_engine, create_sessionmaker


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
```

`create_app` then passes `lifespan=lifespan` into the `FastAPI(...)` constructor. See `factory-and-config.md` for the full factory.

## Transaction Boundary

Pick one transaction ownership model and use it consistently. The recommended default is service-owned transactions: repositories read and write through the provided session, while services decide when to commit or roll back a complete business operation. This keeps the rule "what is atomic" answerable by reading the service, not by chasing through repositories.

### Service-Owned Transaction Helper

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

### Service Pattern

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import transaction
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserRead


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)

    async def create_user(self, payload: UserCreate) -> UserRead:
        async with transaction(self.db):
            user = await self.users.create(payload)
        return UserRead.model_validate(user)
```

## Repository Rules

- Repositories should not call `commit()` unless the project explicitly chooses repository-owned transactions.
- Repositories may call `flush()` when they need generated IDs inside the same transaction.
- Repositories should not import FastAPI; they take a session in `__init__`.
- Services own business-level atomicity.
- Tests should cover rollback behavior for multi-step writes.

## `app/db/base.py`

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models here so Alembic can discover metadata.
# from app.modules.users.models import User
```

## Model Pattern

```python
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
```

## Alembic Notes

- `alembic/env.py` should load `target_metadata` from `app.db.base.Base.metadata`.
- Ensure new model modules are imported by `app/db/base.py` or another single metadata import location, otherwise Alembic autogeneration will silently miss tables.
- Do not create tables directly from application startup in production code; use migrations.
