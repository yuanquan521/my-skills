# Unified Responses Template

统一响应封装模块，所有接口返回必须走此封装，禁止视图层手写零散返回结构。

**业务码约定**：`code` 字段只有两个值：`0` 表示成功，`1` 表示失败。具体的错误语义由 HTTP 状态码承载。

## 响应封装示例 (`app/core/responses.py`)

```python
from flask import jsonify


def success(data=None, message="success", http_status=200):
    """
    统一成功响应
    :param data: 响应数据
    :param message: 提示信息
    :param http_status: HTTP 状态码，默认 200
    """
    return jsonify({
        "code": 0,
        "message": message,
        "data": data,
    }), http_status


def fail(message="Bad Request", http_status=400, data=None, details=None):
    """
    统一失败响应
    :param message: 错误提示
    :param http_status: HTTP 状态码，默认 400
    :param data: 响应数据（失败时通常为 None）
    :param details: 错误详情（如字段校验明细）
    """
    response = {
        "code": 1,
        "message": message,
        "data": data,
    }
    if details is not None:
        response["details"] = details
    return jsonify(response), http_status


def paginate(query, page: int, per_page: int, serialize_fn=None):
    """
    统一分页响应封装

    :param query: SQLAlchemy 查询对象（未执行 .all()）
    :param page: 当前页码（从 1 开始）
    :param per_page: 每页条数
    :param serialize_fn: 可选的序列化函数，用于把模型实例转换成 dict
    :return: Flask JSON Response
    """
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = pagination.items

    if serialize_fn:
        items = [serialize_fn(item) for item in items]

    return success(data={
        "items": items,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages,
    })
```

## 响应示例

成功响应（HTTP 200）：
```json
{"code": 0, "message": "success", "data": {"id": "xxx", "name": "张三"}}
```

失败响应（HTTP 404）：
```json
{"code": 1, "message": "用户不存在", "data": null}
```

失败响应（HTTP 422，带详情）：
```json
{"code": 1, "message": "参数校验失败", "data": null, "details": {"username": "不能为空"}}
```

## 时间字段（UTC+8 可读字符串）

接口特别要求返回可直接展示的时间时：时间字段必须返回已转换为 UTC+8 的可读字符串，格式 `YYYY-MM-DD HH:MM:SS`（如 `2026-11-09 14:30:00`），禁止裸 ISO UTC 字符串或时间戳。存储与内部逻辑仍使用 UTC，转换只发生在序列化层（`to_dict()` 或 `paginate(query, page, per_page, serialize_fn=...)` 的序列化函数中），保证所有接口输出同一形状。

工具函数放在 `app/core/utils/helpers.py`：

```python
from datetime import datetime, timedelta, timezone

UTC_PLUS_8 = timezone(timedelta(hours=8))


def to_cn_time(value: datetime) -> str:
    """UTC 时间（naive 视为 UTC）转 UTC+8 可读字符串。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(UTC_PLUS_8).strftime("%Y-%m-%d %H:%M:%S")
```

## 使用示例

### 在视图中返回成功响应

```python
from app.core.responses import success, paginate

class UserResource(Resource):
    def get(self, user_id):
        user = User.get_by_id(user_id)
        if not user:
            raise NotFoundException("用户不存在")
        return success(data=user.to_dict())

    def post(self):
        # ... 创建逻辑
        return success(data=new_user.to_dict(), message="创建成功", http_status=201)
```

### 分页查询

```python
class UserListResource(Resource):
    def get(self):
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        query = User.query.order_by(User.created_at.desc())
        return paginate(query, page, per_page, serialize_fn=lambda u: u.to_dict())
```
