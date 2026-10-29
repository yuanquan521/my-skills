# Security Baseline Reference

Use this reference when setting up configuration, middleware, logging, authentication-adjacent code, or production hardening for a FastAPI backend.

## Rules

- Keep secrets in `.env` or the deployment secret manager, never in source code.
- Do not log passwords, tokens, API keys, cookies, or full database URLs.
- Configure CORS from settings, not inline literals scattered through the app.
- Configure trusted hosts from settings when deploying behind public traffic.
- Hash passwords with a dedicated password hashing library when authentication is present.
- Do not add authentication unless the user asks for it, but keep the project ready for it (settings field, dependency placeholder, security headers).

## Settings Fields

The fields used by the security baseline (`cors_origins`, `trusted_hosts`, `secret_key`) live in the main `Settings` class — see `factory-and-config.md`. Keep them next to the rest of the settings rather than in a separate security-only settings module.

## Factory Middleware

Both `TrustedHostMiddleware` and `CORSMiddleware` are wired in `app/factory.py` (see `factory-and-config.md`). Two details that matter:

```python
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
```

The `allow_credentials` guard is not cosmetic. Browsers reject responses that combine `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true`, and the request fails for the user with a confusing CORS error. Always derive `allow_credentials` from whether `*` is in `cors_origins`. Production deployments should use an explicit allow-list anyway.

## Password Hashing

Use a maintained password-hashing library. Two reasonable choices:

- `pwdlib` — modern, supports argon2/bcrypt/scrypt with one API.
- `passlib[bcrypt]` — battle-tested, more documentation in the wild.

Pick one per project. Wrapping the choice keeps callers stable if you swap libraries later.

The full JWT/OAuth2 recipe — token issuance, `get_current_user`/`CurrentUser`, route protection, and auth tests — lives in `authentication.md`; this file stays the baseline.

```python
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)
```

## Logging Redaction Notes

- Log stable IDs (user ID, request ID) rather than raw secrets or tokens.
- Log exception context, not full request bodies by default — bodies often contain PII.
- Redact `Authorization` headers and cookies before logging.
- Never include raw `DATABASE_URL` values in logs; the URL contains credentials.
- If you add a structured/JSON log path, include a redaction step there too — JSON logs are often shipped to systems with weaker access controls than application logs.
