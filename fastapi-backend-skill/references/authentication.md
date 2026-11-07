# Authentication Reference

Use this reference when adding JWT/OAuth2 password-flow authentication, issuing tokens, or protecting routes with a current-user dependency.

## Rules

- Add authentication only when the user asks for it; keep the project ready for it beforehand (see `security.md`).
- Password hashing wrappers and JWT encode/decode live in `app/core/security.py`, which must not import FastAPI so it stays importable from CLI scripts and tests.
- Auth failures are `AppError` with `status_code=401` so they flow through the global handler into the unified `ApiResponse` envelope — never bare `HTTPException`.
- The login endpoint is a normal single-file domain (`app/api/v1/auth.py`) registered through the central router like any other.
- Never log tokens, passwords, or `Authorization` headers (see `security.md` redaction notes).
- Secrets come from `Settings` (`.env`), never literals.

## Dependencies

```bash
uv add pyjwt pwdlib python-multipart
```

`python-multipart` is required by FastAPI to parse `OAuth2PasswordRequestForm` form bodies.

## Settings Fields

Extend the main `Settings` (see `factory-and-config.md`) — `secret_key` already exists there:

```python
class Settings(BaseSettings):
    ...
    secret_key: str  # required once authentication is present
    access_token_expire_minutes: int = 30
```

## `app/core/security.py`

Hashing wrappers come from `security.md`; this module also owns the token format:

```python
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str: ...      # pwdlib / passlib per security.md
def verify_password(password: str, hashed_password: str) -> bool: ...


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
```

`jwt.decode` raises `jwt.PyJWTError` on expiry/tampering; the dependency below translates that into an `AppError`.

## `app/api/dependencies.py`

```python
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select

from app.core.exceptions import AppError
from app.core.security import decode_access_token
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# DbSession / RequestId aliases also live here (see module-template.md)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None or payload.get("type") != "access":
            raise AppError("UNAUTHORIZED", "Invalid credentials", status_code=401)
    except jwt.PyJWTError as exc:
        raise AppError("UNAUTHORIZED", "Invalid credentials", status_code=401) from exc

    result = await db.execute(select(User).where(User.id == subject))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError("UNAUTHORIZED", "Invalid credentials", status_code=401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
```

Notes:

- `DbSession` is the alias this file already exports; `get_db` is its underlying dependency.
- The user lookup is one `select` — thin enough to live directly in the dependency. If auth grows (roles, permissions, caching), move the lookup into the users domain's `service.py` and call it from here.
- If the project needs the RFC 6750 `WWW-Authenticate: Bearer` header on 401 responses, extend `AppError` with an optional `headers: dict[str, str] | None` and pass it through `app_error_handler` in `exception_handlers.py`. Do not hand-roll a separate 401 path.

## Login Domain: `app/api/v1/auth.py`

```python
from typing import Annotated

from fastapi import Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select

from app.api.dependencies import DbSession, RequestId
from app.api.route_registry import RouteSpec
from app.core.exceptions import AppError
from app.core.responses import ApiResponse, ok
from app.core.security import create_access_token, verify_password
from app.models import User


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


async def login_for_access_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
    request_id: RequestId,
) -> ApiResponse[Token]:
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise AppError("UNAUTHORIZED", "Incorrect username or password", status_code=401)
    token = create_access_token(subject=str(user.id))
    return ok(Token(access_token=token), request_id=request_id)


routes = [
    RouteSpec(
        path="/auth/token",
        endpoint=login_for_access_token,
        methods=["POST"],
        response_model=ApiResponse[Token],
        status_code=status.HTTP_200_OK,
        name="login_for_access_token",
        tags=["auth"],
    ),
]
```

Register from `app/api/router.py` like any other domain: `from app.api.v1.auth import routes as auth_routes`. One generic message for both wrong-username and wrong-password avoids leaking which one matched.

## User Model

`app/models/users.py` stores only the hash; `schemas.py` never exposes it:

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
```

Create the column via an Alembic migration (never `create_all`), and backfill hashes for existing rows before enforcing login.

## Protecting Routes

Two styles; pick per endpoint:

```python
# 1) Parameter style — when the handler needs the user object
async def get_me(
    current_user: CurrentUser,
    request_id: RequestId,
) -> ApiResponse[UserRead]:
    return ok(UserRead.model_validate(current_user), request_id=request_id)


# 2) RouteSpec.dependencies — blanket guard without touching the signature
RouteSpec(
    path="/orders",
    endpoint=endpoints.create_order,
    methods=["POST"],
    dependencies=[Depends(get_current_user)],
    ...
)
```

Import `Depends` inside `routes.py` only for `RouteSpec.dependencies` — that is route metadata, not endpoint code, and keeps decorators out of the codebase.

## Authorization (403 vs 401)

Authentication answers "who"; authorization answers "may this user do this". Keep them separate so clients get precise signals: `401 UNAUTHORIZED` is a missing/invalid token (raised by `get_current_user`), `403 FORBIDDEN` is a valid identity without permission.

```python
# app/api/dependencies.py
async def require_admin(current_user: CurrentUser) -> User:
    if not current_user.is_admin:
        raise AppError("FORBIDDEN", "Insufficient permissions", status_code=403)
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
```

Ownership checks compare the path target with the current user inside the endpoint or service:

```python
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user: CurrentUser,
) -> ApiResponse[UserRead]:
    if current_user.id != user_id and not current_user.is_admin:
        raise AppError("FORBIDDEN", "Not authorized", status_code=403)
    ...
```

## Testing

```python
async def test_protected_route_requires_token(client):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "UNAUTHORIZED"


async def test_protected_route_with_user(client, app):
    async def override_get_current_user():
        return User(id=..., email="t@example.com", hashed_password="x")

    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
```

Override `get_current_user` (the dependency function), not the `CurrentUser` alias. Test the real login path against a real PostgreSQL test database with a seeded hashed user.

## Notes

- Access tokens only; add refresh tokens as a second token type in `create_access_token` when needed.
- Tokens travel in the `Authorization: Bearer <token>` header via `OAuth2PasswordBearer`; never in query strings or logs.
- Keep token lifetime short (minutes); reject `type != "access"` so future refresh tokens cannot be replayed as access tokens.
