# Database BaseModel Template

所有数据库模型必须继承自定义的 `BaseModel`。这个基类统一了常见字段（主键、创建时间、更新时间）以及常见的便利方法。

## BaseModel 示例 (`app/core/models.py`)

```python
from datetime import datetime, timedelta, timezone
import uuid
from app.extensions.database import db
from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column

UTC_PLUS_8 = timezone(timedelta(hours=8))


def now_cn():
    """当前 UTC+8 本地时间（naive），数据库存储与 API 输出共用此时钟。"""
    return datetime.now(UTC_PLUS_8).replace(tzinfo=None)

class BaseModel(db.Model):
    """
    通用数据库模型基类，提供公共字段。
    """
    __abstract__ = True

    # 推荐使用 UUID 作为主键，有利于分布式和安全性
    # 使用 sqlalchemy.Uuid 替代 String(36)
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="主键 ID"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=now_cn,
        nullable=False,
        comment="创建时间（UTC+8）"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=now_cn,
        onupdate=now_cn,
        nullable=False,
        comment="更新时间（UTC+8）"
    )

    def save(self):
        """保存当前对象到数据库"""
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        """从数据库删除当前对象"""
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, record_id):
        """根据 ID 获取对象"""
        return db.session.get(cls, record_id)
```

## 使用说明

1. 业务模型均继承 `BaseModel`，并重写 `__tablename__`（推荐使用小写复数或具有明确领域意义的命名）。
2. 可根据项目需要增加软删除标记 `is_deleted` 等共有业务字段。
3. 时间字段统一存储 UTC+8 本地时间（naive `DateTime` 列），与 API 输出同一时钟；不要改回 `DateTime(timezone=True)`、`func.now()` 或 `datetime.now(timezone.utc)`，否则时间链路会出现两种时区。
