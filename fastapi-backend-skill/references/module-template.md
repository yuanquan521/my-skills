# Module Template Reference

Use this reference when creating a new domain such as users, orders, products, or invoices.

## Rules

- Place every domain under `app/api/v1/`. Start with a single module; promote to a package only when a growth trigger fires.
- Route metadata always lives in a `routes` list of `RouteSpec` entries — never in decorators.
- One domain per file or package; never split one domain across sibling folders.
- Register the domain from the central API router (`app/api/router.py`).
- ORM models never live in domain files. They go to `app/models/<domain>.py` and are re-exported from `app/models/__init__.py`, which `app/db/base.py` imports once.
- Shared HTTP dependencies (`DbSession`, `RequestId`, future auth deps) are `Annotated` aliases exported from `app/api/dependencies.py`; endpoint files import them from there, never from their defining modules.
- Add layers for logic thickness, not symmetry: no `repository.py` by default; add `service.py` only when the domain has reusable business rules or multi-step transaction orchestration.

## Tier 1 — Single-File Domain (default)

A new domain is one module: `app/api/v1/orders.py` holds schemas, endpoint functions, and the `routes` list; its ORM model lives in `app/models/orders.py`. Thin CRUD queries the session directly inside endpoint functions, with an explicit per-write transaction.

```python
# app/api/v1/orders.py
from uuid import UUID

from fastapi import status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.dependencies import DbSession, RequestId
from app.api.route_registry import RouteSpec
from app.core.exceptions import AppError
from app.core.responses import ApiResponse, ok
from app.db.session import transaction
from app.models.orders import Order


class OrderCreate(BaseModel):
    customer_id: UUID
    total_cents: int = Field(ge=0)


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    total_cents: int
    status: str


async def create_order(
    payload: OrderCreate,
    db: DbSession,
    request_id: RequestId,
) -> ApiResponse[OrderRead]:
    async with transaction(db):
        order = Order(**payload.model_dump())
        db.add(order)
        await db.flush()
    return ok(OrderRead.model_validate(order), request_id=request_id)


async def get_order(
    order_id: UUID,
    db: DbSession,
    request_id: RequestId,
) -> ApiResponse[OrderRead]:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise AppError("ORDER_NOT_FOUND", "Order not found", status_code=404)
    return ok(OrderRead.model_validate(order), request_id=request_id)


routes = [
    RouteSpec(
        path="/orders",
        endpoint=create_order,
        methods=["POST"],
        response_model=ApiResponse[OrderRead],
        status_code=status.HTTP_201_CREATED,
        name="create_order",
        tags=["orders"],
    ),
    RouteSpec(
        path="/orders/{order_id}",
        endpoint=get_order,
        methods=["GET"],
        response_model=ApiResponse[OrderRead],
        name="get_order",
        tags=["orders"],
    ),
]
```

Re-export the model from `app/models/__init__.py` so Alembic discovers it. One domain file, one model file, one registration line in the central router — that is the whole cost of a new domain.

## Growth Triggers

Promote `orders.py` to a package when any of these fire:

- The module exceeds roughly 150–200 lines.
- The domain has multiple endpoint groups (for example admin and public surfaces).
- Business logic is reused across endpoints or imported by other domains.
- A sub-concept of the domain grows its own service and routes (Dispatch's `case/priority/` pattern) — promote it to a nested package rather than piling more files into the parent; its model simply joins `app/models/`.

Do not promote preemptively; a 60-line dictionary-table domain staying single-file is correct. Sub-packages appear the same way: only when the sub-concept's own files justify them.

## Tier 2 — Domain Package

```
app/api/v1/orders/
├── endpoints.py     # HTTP-facing functions
├── routes.py        # RouteSpec list
└── schemas.py       # Pydantic request/response models
```

Same content as Tier 1, redistributed. Data access stays in `endpoints.py` until Tier 3. On-demand files (`dependencies.py`, `constants.py`, `exceptions.py`, `utils.py`, per-domain `config.py`) may appear inside the package when a real need shows up — never create them preemptively for symmetry.

```python
# app/api/v1/orders/routes.py
from fastapi import status

from app.api.route_registry import RouteSpec
from app.api.v1.orders import endpoints
from app.api.v1.orders.schemas import OrderRead
from app.core.responses import ApiResponse


routes = [
    RouteSpec(
        path="/orders",
        endpoint=endpoints.create_order,
        methods=["POST"],
        response_model=ApiResponse[OrderRead],
        status_code=status.HTTP_201_CREATED,
        name="create_order",
        tags=["orders"],
    ),
]
```

```python
# app/models/orders.py
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_cn
from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    total_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=now_cn,
    )
```

```python
# app/models/__init__.py — re-export every model; app/db/base.py imports this once
from app.models.orders import Order
from app.models.users import User
```

## Tier 3 — Full Domain

Trigger: business rules reused across endpoints or modules, multi-step transaction orchestration, or service tests that need a faked session.

Add `service.py` owning business rules and transactions; endpoints become thin delegates.

```python
# app/api/v1/orders/service.py
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.orders.schemas import OrderCreate, OrderRead
from app.core.exceptions import AppError
from app.db.session import transaction
from app.models.orders import Order


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_order(self, payload: OrderCreate) -> OrderRead:
        async with transaction(self.db):
            order = Order(**payload.model_dump())
            self.db.add(order)
            await self.db.flush()
        return OrderRead.model_validate(order)

    async def get_order(self, order_id: UUID) -> OrderRead:
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order is None:
            raise AppError("ORDER_NOT_FOUND", "Order not found", status_code=404)
        return OrderRead.model_validate(order)
```

```python
# app/api/v1/orders/endpoints.py (Tier 3 form)
from uuid import UUID

from app.api.dependencies import DbSession, RequestId
from app.api.v1.orders.schemas import OrderCreate, OrderRead
from app.api.v1.orders.service import OrderService
from app.core.responses import ApiResponse, ok


async def create_order(
    payload: OrderCreate,
    db: DbSession,
    request_id: RequestId,
) -> ApiResponse[OrderRead]:
    order = await OrderService(db).create_order(payload)
    return ok(order, request_id=request_id)


async def get_order(
    order_id: UUID,
    db: DbSession,
    request_id: RequestId,
) -> ApiResponse[OrderRead]:
    order = await OrderService(db).get_order(order_id)
    return ok(order, request_id=request_id)
```

## About `repository.py`

Not part of the default contract. No widely-followed FastAPI source — the official team template, the official docs, the highest-star community guide, or Netflix Dispatch — uses a repository layer; services and endpoints query SQLAlchemy directly. If a project explicitly chooses repositories anyway, they must not call `commit()`, must not import FastAPI, and take a session in `__init__`.

## Central Router Registration (all tiers)

```python
from app.api.route_registry import register_routes
from app.api.v1.health import routes as health_routes          # single-file domain
from app.api.v1.orders.routes import routes as order_routes    # domain package


register_routes(api_router, health_routes)
register_routes(api_router, order_routes)
```

For a package, import the `routes` list explicitly from `.routes`. `from app.api.v1.orders import routes` would import the `routes.py` module instead of the list and must not be used in the registry.

## Follow-Up Steps

- Add the model to `app/models/<domain>.py` and re-export it from `app/models/__init__.py` so Alembic discovers it.
- Create an Alembic migration for the new table or schema change.
- Add tests for the touched routes and services (when present).
- Run the no-route-decorators static check from `testing.md`.
