# Unified Exceptions Template

为保持全站统一返回格式 `code/message/data`，所有业务异常统一通过 `APIException` 及其子类抛出，由全局异常处理器接管格式化。

**约定**：
- JSON body 中 `code` 固定为 `1`（失败），具体错误语义由 HTTP 状态码承载。
- 所有 JWT 认证失败（缺失、格式无效、过期、吊销、校验失败）统一返回 HTTP `401`，方便前端/客户端只拦截 401 处理登录态刷新或跳转，不与参数校验错误 `422` 混淆。

## 完整模块示例 (`app/core/exceptions.py`)

以下全部代码可直接作为单个 `app/core/exceptions.py` 使用（无自我循环导入）：

```python
from flask import Flask, current_app
from flask_jwt_extended import JWTManager
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from app.core.responses import fail


class APIException(Exception):
    """通用业务异常基类"""

    def __init__(
        self,
        message: str = "Bad Request",
        http_status: int = 400,
        data: dict | list | None = None,
        details: dict | list | str | None = None,
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


def register_error_handlers(app: Flask) -> None:
    """在 create_app() 中调用，接管业务异常、Pydantic 校验、HTTP 错误与未知异常。"""

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


def register_jwt_error_handlers(jwt: JWTManager) -> None:
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
            http_status=401,
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

> 若项目未启用 JWT 认证，省略 `flask_jwt_extended` 导入和 `register_jwt_error_handlers` 即可。
