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

    def save(self, *, commit: bool = True):
        """
        将当前对象加入会话；单步简单写入可直接 commit=True，
        在多步 Service 事务中请传 commit=False 或直接使用 db.session.add() + Service 层统一 commit()。
        """
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, *, commit: bool = True):
        """从会话删除当前对象；多步事务中请传 commit=False 由 Service 层统一提交。"""
        db.session.delete(self)
        if commit:
            db.session.commit()

    @classmethod
    def get_by_id(cls, record_id):
        """根据 ID 获取对象"""
        return db.session.get(cls, record_id)
```

## 使用说明

1. 业务模型均继承 `BaseModel`，并重写 `__tablename__`（推荐使用小写复数或具有明确领域意义的命名）。
2. 所有物理列必须带 `comment="说明"`，但 `relationship()` 上禁止传 `comment`。
3. 涉及多表或多步写入时，在 Service 层统一 `db.session.commit()` / `rollback()`，不要在循环或中间步骤调用默认 `save()` 导致提前提交破坏事务原子性。
4. 时间字段统一存储 UTC+8 本地时间（naive `DateTime` 列），与 API 输出同一时钟；不要改回 `DateTime(timezone=True)`、`func.now()` 或 `datetime.now(timezone.utc)`，否则时间链路会出现两种时区。
