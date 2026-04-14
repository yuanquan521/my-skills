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

在 `app/__init__.py` 的 `create_app` 中，调用 `register_error_handlers(app)` 对 `APIException` 以及其他内置异常（如 404, 500 等）进行全局捕获，以确保始终返回标准的响应结果：

```python
from flask import jsonify, Flask, current_app
from werkzeug.exceptions import HTTPException
from app.core.exceptions import APIException

def register_error_handlers(app: Flask):
    @app.errorhandler(APIException)
    def handle_api_exception(e: APIException):
        response = {
            "code": 1,
            "message": e.message,
            "data": e.data,
        }
        if e.details is not None:
            response["details"] = e.details
        return jsonify(response), e.http_status

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        response = {
            "code": 1,
            "message": getattr(e, "description", str(e)),
            "data": None,
        }
        return jsonify(response), getattr(e, "code", 500)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e: Exception):
        # 记录未预期的系统异常日志
        current_app.logger.exception("Unexpected error occurred")
        response = {
            "code": 1,
            "message": "Internal Server Error",
            "data": None,
        }
        return jsonify(response), 500
```
