# Database BaseModel Template

所有数据库模型必须继承自定义的 `BaseModel`。这个基类统一了常见字段（主键、创建时间、更新时间）以及常见的便利方法。

## BaseModel 示例 (`app/core/models.py`)

```python
from datetime import datetime, timezone
import uuid
from app.extensions.database import db
from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column


def utcnow():
    return datetime.now(timezone.utc)

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
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        comment="创建时间"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
        comment="更新时间"
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
