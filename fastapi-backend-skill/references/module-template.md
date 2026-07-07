# Module Template Reference

Use this reference when creating a new domain module such as users, orders, products, or invoices.

## Rules

- Keep HTTP wiring in `endpoints.py`.
- Keep route metadata in `routes.py`.
- Keep Pydantic models in `schemas.py`.
- Keep SQLAlchemy models in `models.py`.
- Keep SQL in `repository.py`.
- Keep business rules and transaction ownership in `service.py`.
- Register the module from the central API router.

The examples below use an `orders` module. Rename consistently for the requested domain.

## `schemas.py`

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    customer_id: UUID
    total_cents: int = Field(ge=0)


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    total_cents: int
    status: str
    created_at: datetime
```

## `models.py`

```python
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    total_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
```

## `repository.py`

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderCreate


class OrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, payload: OrderCreate) -> Order:
        order = Order(**payload.model_dump())
        self.db.add(order)
        await self.db.flush()
        return order

    async def get(self, order_id) -> Order | None:
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()
```

## `service.py`

```python
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.db.session import transaction
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderCreate, OrderRead


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)

    async def create_order(self, payload: OrderCreate) -> OrderRead:
        async with transaction(self.db):
            order = await self.orders.create(payload)
        return OrderRead.model_validate(order)

    async def get_order(self, order_id: UUID) -> OrderRead:
        order = await self.orders.get(order_id)
        if order is None:
            raise AppError("ORDER_NOT_FOUND", "Order not found", status_code=404)
        return OrderRead.model_validate(order)
```

## `endpoints.py`

```python
from uuid import UUID

from app.core.responses import ApiResponse, ok
from app.db.session import DbSession
from app.middleware.request_context import RequestId
from app.modules.orders.schemas import OrderCreate, OrderRead
from app.modules.orders.service import OrderService


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

## `routes.py`

```python
from fastapi import status

from app.api.route_registry import RouteSpec
from app.core.responses import ApiResponse
from app.modules.orders import endpoints
from app.modules.orders.schemas import OrderRead


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
    RouteSpec(
        path="/orders/{order_id}",
        endpoint=endpoints.get_order,
        methods=["GET"],
        response_model=ApiResponse[OrderRead],
        name="get_order",
        tags=["orders"],
    ),
]
```

## Central Router Registration

```python
from app.modules.orders.routes import routes as order_routes

register_routes(api_router, order_routes)
```

## Follow-Up Steps

- Import the model in `app/db/base.py` for Alembic discovery.
- Create an Alembic migration for the new table or schema change.
- Add route, service, and repository tests for the module.
- Run the no-route-decorators static check from `testing.md`.
