# Unified Exceptions Template

为了实现统一返回格式 `code/message/data`，所有业务代码或路由层抛出的业务异常，应当统一通过自定义异常类处理。然后由全局错误处理函数（Global Error Handler）接管，格式化输出给客户端。

**业务码约定**：JSON body 中 `code` 固定为 `1`（失败），错误语义通过 HTTP 状态码区分。

## Exceptions 示例 (`app/core/exceptions.py`)

```python
class APIException(Exception):
    """
    通用业务异常基类
    """
    def __init__(
        self,
        message: str = "Bad Request",
        http_status: int = 400,
        data: dict | list | None = None,
        details: dict | list | str | None = None
    ):
        self.message = message
        self.http_status = http_status
        self.data = data
        self.details = details
        super().__init__(self.message)

class NotFoundException(APIException):
    def __init__(self, message: str = "资源不存在", details=None):
        super().__init__(message=message, http_status=404, details=details)

class AuthException(APIException):
    def __init__(self, message: str = "认证失败，请重新登录", details=None):
        super().__init__(message=message, http_status=401, details=details)

class ForbiddenException(APIException):
    def __init__(self, message: str = "无权进行该操作", details=None):
        super().__init__(message=message, http_status=403, details=details)

class ValidationException(APIException):
    def __init__(self, message: str = "参数校验失败", details=None):
        super().__init__(message=message, http_status=422, details=details)

class DuplicateRecordException(APIException):
    def __init__(self, message: str = "记录已存在", details=None):
        super().__init__(message=message, http_status=409, details=details)
```

## 全局异常捕获

在 `app/__init__.py` 的 `create_app` 中，调用 `register_error_handlers(app)` 对 `APIException`、Pydantic 校验错误以及其他内置异常（如 404、500）进行全局捕获。`JWTManager` 初始化后还必须调用 `register_jwt_error_handlers(jwt)`，覆盖其默认错误响应，确保 JWT 错误同样返回标准结构：

```python
from flask import Flask, current_app
from flask_jwt_extended import JWTManager
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from app.core.exceptions import APIException
from app.core.responses import fail


def register_error_handlers(app: Flask):
    @app.errorhandler(APIException)
    def handle_api_exception(e: APIException):
        return fail(
            message=e.message,
            http_status=e.http_status,
            data=e.data,
            details=e.details,
        )

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        return fail(
            message="参数校验失败",
            http_status=422,
            details=e.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            ),
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        return fail(
            message=getattr(e, "description", str(e)),
            http_status=getattr(e, "code", 500),
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e: Exception):
        current_app.logger.exception("Unexpected error occurred")
        return fail(message="Internal Server Error", http_status=500)


def register_jwt_error_handlers(jwt: JWTManager):
    """在 JWTManager 初始化后调用，覆盖 Flask-JWT-Extended 的默认响应。"""

    @jwt.unauthorized_loader
    def handle_missing_token(reason: str):
        return fail(
            message="缺少认证令牌",
            http_status=401,
            details={"reason": reason},
        )

    @jwt.invalid_token_loader
    def handle_invalid_token(reason: str):
        return fail(
            message="认证令牌无效",
            http_status=422,
            details={"reason": reason},
        )

    @jwt.expired_token_loader
    def handle_expired_token(_jwt_header, _jwt_payload):
        return fail(message="认证令牌已过期", http_status=401)

    @jwt.revoked_token_loader
    def handle_revoked_token(_jwt_header, _jwt_payload):
        return fail(message="认证令牌已吊销", http_status=401)

    @jwt.needs_fresh_token_loader
    def handle_fresh_token_required(_jwt_header, _jwt_payload):
        return fail(message="需要新的认证令牌", http_status=401)

    @jwt.token_verification_failed_loader
    def handle_token_verification_failed(_jwt_header, _jwt_payload):
        return fail(message="认证令牌校验失败", http_status=401)
```
