# Flask-Migrate 数据库迁移参考

数据库 Schema 变更**必须**通过 Flask-Migrate（Alembic）管理，禁止手动执行 DDL 或使用 `db.create_all()`。

## 扩展初始化 (`app/extensions/database.py`)

```python
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
```

## 工厂函数中注册 (`app/__init__.py`)

```python
from app.extensions.database import db, migrate

def create_app():
    app = Flask(__name__)
    # ... 加载配置 ...

    db.init_app(app)
    migrate.init_app(app, db)

    # ... 注册蓝图等 ...
    return app
```

## 命令行用法

所有迁移命令均通过 `flask db` 子命令执行，需确保 `FLASK_APP` 环境变量已设置（如 `manage.py` 或 `wsgi.py`）。

### 首次初始化

项目首次使用时，生成 `migrations/` 目录：

```bash
flask db init
```

> 生成后应将整个 `migrations/` 目录纳入版本控制（Git）。

### 生成迁移脚本

修改模型后，自动检测变更并生成迁移脚本：

```bash
flask db migrate -m "简要描述本次变更"
```

**注意**：生成后**必须人工审查** `migrations/versions/` 下新生成的脚本，确认 `upgrade()` 和 `downgrade()` 逻辑正确。Alembic 的自动检测并非万能，以下变更可能无法自动识别：

- 表名重命名
- 列名重命名
- `Enum` 类型值变更
- 约束名变更
- 数据迁移（需手写 `op.execute()`）

### 应用迁移

将数据库升级到最新版本：

```bash
flask db upgrade
```

### 回滚迁移

回退到上一个版本：

```bash
flask db downgrade
```

回退到指定版本：

```bash
flask db downgrade <revision_id>
```

### 查看当前版本

```bash
flask db current
```

### 查看迁移历史

```bash
flask db history
```

## APScheduler Job Store 建表迁移

`SQLAlchemyJobStore` 使用独立 metadata，`flask db migrate` 不会自动发现 `apscheduler_jobs`。首次启用持久化调度器时，先创建空迁移：

```bash
flask db revision -m "add apscheduler job store"
```

保留生成的 `revision` 和 `down_revision`，将两个函数替换为以下 APScheduler 3.x 兼容实现，并在启动调度器前执行 `flask db upgrade`：

```python
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "apscheduler_jobs",
        sa.Column("id", sa.String(length=191), nullable=False),
        sa.Column("next_run_time", sa.Float(25), nullable=True),
        sa.Column("job_state", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_apscheduler_jobs_next_run_time",
        "apscheduler_jobs",
        ["next_run_time"],
    )


def downgrade():
    op.drop_index(
        "ix_apscheduler_jobs_next_run_time",
        table_name="apscheduler_jobs",
    )
    op.drop_table("apscheduler_jobs")
```

如果修改了 job store 的 `tablename`，迁移中的表名和索引名必须同步修改。不要通过 `db.create_all()` 或启动时的自动建表替代此迁移。

## 强制约束

| 规则 | 说明 |
|------|------|
| 禁止 `db.create_all()` | 生产环境和开发环境均不得使用 `db.create_all()` 创建表，必须通过迁移脚本管理 |
| 迁移脚本必须审查 | 每次 `flask db migrate` 后，必须人工检查生成的脚本再执行 `upgrade` |
| 迁移目录纳入 Git | `migrations/` 目录及所有版本脚本必须提交到版本控制 |
| 迁移消息必须有意义 | `flask db migrate -m` 的消息必须简要描述本次 Schema 变更内容 |
| 一次变更一个迁移 | 避免在单个迁移脚本中堆积过多不相关的变更 |
| downgrade 必须可用 | 每个迁移脚本的 `downgrade()` 必须能正确回滚对应的 `upgrade()` |

## 常见问题

### Q: 开发时模型频繁变动，如何管理？

开发初期可以频繁生成迁移脚本，待模型稳定后在发布前合并（squash）迁移：

```bash
# 回退到初始状态
flask db downgrade base
# 删除 migrations/versions/ 下的所有文件
# 重新生成一个干净的迁移
flask db migrate -m "initial schema"
flask db upgrade
```

### Q: 多人协作时迁移冲突怎么办？

1. 先 `git pull` 获取他人的迁移脚本
2. 执行 `flask db upgrade` 应用他人的迁移
3. 再 `flask db migrate` 生成自己的新迁移
4. 如有分支冲突，手动编辑迁移脚本的 `down_revision` 链

### Q: 测试环境是否需要迁移？

测试环境同样必须使用迁移管理 Schema。在 `conftest.py` 中可通过以下方式自动应用：

```python
import os

import pytest
from dotenv import load_dotenv
from flask_migrate import upgrade


@pytest.fixture(scope="session")
def app():
    load_dotenv()
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.fail("测试前必须设置 TEST_DATABASE_URL，禁止回退到开发数据库")

    from app import create_app

    app = create_app("testing")
    assert app.config["TESTING"] is True
    with app.app_context():
        upgrade()  # 仅在 TestingConfig 指定的隔离数据库上执行迁移
        yield app
```
