---
name: flask-backend-skill
description: >-
  Establishes a pure Flask backend API project structure in the current directory with
  an app factory (`create_app`), `.env`-driven config layers, PostgreSQL via
  Flask-SQLAlchemy + psycopg3 + Flask-Migrate, JWT auth, Pydantic validation,
  Loguru logging, Gunicorn, optional Redis, and an optional standalone APScheduler
  process sharing Flask config and task code. Use whenever creating, refactoring, or
  extending a Flask + PostgreSQL backend, or when the user mentions Flask 后端,
  Flask-SQLAlchemy, Flask-Migrate, APScheduler, 独立调度进程, or Flask 统一返回
  (code/message/data).
---

# Flask Backend API Skill

在当前工作目录中构建或重构纯后端 Flask API 项目，统一分层、响应结构、异常处理、日志与数据库迁移规范；当业务需要定时任务时，通过独立 APScheduler 进程与 Web 进程解耦。

> 本文件作为总控指南。仅在当前任务涉及对应模块时，按需读取 `references/` 下的实现模板，避免一次性加载全部参考文件。

## 按需查阅参考 (Progressive Disclosure)

| 场景 | 参考文件 |
| --- | --- |
| 工厂配置分层、`.env.example` 与环境变量校验 | [references/config.md](references/config.md) |
| Flask-Migrate (Alembic) 迁移流程与 `apscheduler_jobs` 建表迁移 | [references/migrate.md](references/migrate.md) |
| `BaseModel` 基类模板与 UTC+8 时间默认值 (`now_cn`) | [references/models.md](references/models.md) |
| 统一业务异常类与 Flask / Pydantic / JWT 全局异常拦截 | [references/exceptions.md](references/exceptions.md) |
| 统一响应封装 (`success` / `fail` / `paginate`) 与 `to_cn_time` | [references/responses.md](references/responses.md) |
| Loguru 多进程日志配置与 Flask `app.logger` 桥接 | [references/logger.md](references/logger.md) |
| Gunicorn 生产配置模板与启动命令 | [references/gunicorn-config.md](references/gunicorn-config.md) |
| 独立 APScheduler 进程架构、约束与 `scripts/run_scheduler.py` 模板 | [references/scheduler-architecture.md](references/scheduler-architecture.md) |
| Flask 侧任务管理 API 端点与并发安全约定 | [references/scheduler-api.md](references/scheduler-api.md) |

## 技术栈与按需模块

- **核心底座**：Python 3.12+、`uv`（`pyproject.toml` + `uv.lock` + `.python-version`）、Flask、Flask-SQLAlchemy、Flask-Migrate、python-dotenv、Pydantic、Loguru、Gunicorn。
- **数据库**：PostgreSQL + psycopg3（包名为 `psycopg`，安装命令 `uv add "psycopg[binary]"`，连接串前缀 `postgresql+psycopg://`）。
- **认证（按需启用）**：Flask-JWT-Extended，`identity` 仅存用户 ID，算法固定 `HS256`，生产默认开启 `JWT_COOKIE_SECURE`。
- **缓存（按需启用）**：Redis，通过 `REDIS_ENABLED` 开关控制加载。
- **定时调度（按需启用）**：APScheduler 独立进程（`BlockingScheduler` + `SQLAlchemyJobStore`），禁止使用 Flask-APScheduler，避免在多 Worker Web 进程中重复触发定时任务。
- **非目标**：不生成前端页面；不要求嵌套创建新项目目录或手工搬运模板仓库。

## 目标目录结构

基础结构按需裁剪——无定时任务时不创建 `app/scheduler/`、`app/tasks/` 与 `scripts/run_scheduler.py`；无鉴权时不强行创建 `auth` 模块：

```text
.
├── .env / .env.example
├── .gitignore
├── .python-version
├── pyproject.toml / uv.lock
├── config.py
├── manage.py                    # 极简开发启动入口：app = create_app(); app.run()
├── wsgi.py                      # 生产 WSGI 入口：暴露 app 供 Gunicorn 加载
├── gunicorn.conf.py             # 生产配置（见 references/gunicorn-config.md）
├── migrations/                  # Flask-Migrate 生成，纳入 Git
├── docs/                        # api.md / development.md / architecture.md
├── scripts/
│   └── run_scheduler.py         # 仅启用调度器时创建
├── tests/                       # 初始脚手架仅预留目录；补测试时放 conftest.py 与用例
└── app/
    ├── __init__.py              # create_app() 工厂函数
    ├── core/
    │   ├── models.py            # BaseModel
    │   ├── exceptions.py        # APIException 与全局错误处理器
    │   ├── responses.py         # success / fail / paginate
    │   ├── security.py          # 密码哈希等安全辅助（按需）
    │   └── utils/helpers.py     # to_cn_time 等公共工具
    ├── extensions/
    │   ├── database.py          # db、migrate 实例
    │   ├── logger.py            # Loguru 拦截与桥接
    │   └── auth.py              # JWTManager（按需）
    ├── models/                  # ORM 模型，按业务分文件并经 __init__.py 导出
    ├── schemas/                 # Pydantic 校验模型
    ├── services/                # 业务逻辑与事务提交边界（复杂业务时拆分）
    ├── scheduler/               # 仅启用调度器时创建（manager / loader / runner）
    ├── tasks/                   # 仅启用调度器时创建（Web 与调度进程共享任务）
    └── api/
        ├── __init__.py          # register_blueprints(app) 集中注册蓝图
        └── <domain>.py          # 按业务拆分的 Blueprint 模块
```

## 核心架构约束

### 1. 应用工厂与配置分层
- `app/__init__.py` 暴露 `create_app(env: str | None = None)`，从根目录 `.env` + 环境变量动态加载 `DevelopmentConfig` / `TestingConfig` / `ProductionConfig`（不要在模块 import 时固化环境变量，否则测试切换 `FLASK_ENV` / `TEST_DATABASE_URL` 会失效，详见 [references/config.md](references/config.md)）。
- 生产环境必须校验非占位 `SECRET_KEY` 与 `JWT_SECRET_KEY`；测试环境必须显式配置与开发库隔离的 `TEST_DATABASE_URL`。
- 始终提供 `.env.example`，禁止在代码中硬编码密钥。

### 2. 数据库、迁移与时间链路
- 所有 Schema 变更通过 Flask-Migrate（`flask db migrate -m "..."` → 人工审查 → `flask db upgrade`）管理，禁止使用 `db.create_all()`，确保变更历史可追溯、可回滚（详见 [references/migrate.md](references/migrate.md)）。
- `db` 与 `migrate` 在 `app/extensions/database.py` 声明并在 `create_app()` 中集中初始化。
- 业务模型继承 [references/models.md](references/models.md) 的 `BaseModel`，采用 SQLAlchemy 2.0 现代注解（`Mapped[...] = mapped_column(...)`）。
- 物理列均添加 `comment="..."` 便于数据库运维排查，但 `relationship()` 上**绝不**传 `comment`（SQLAlchemy 会报参数错误）。
- 本规范统一约定查询写法为 `db.session.query(Model).filter_by(...)`，避免使用已弃用的 `Model.query` 属性，同时保持团队内检索写法一致。
- 多步写操作应在 Service 层统一控制 `db.session.commit()` / `rollback()`，避免在视图函数或模型便捷方法中零散提交而破坏事务原子性。
- **全链路 UTC+8（`Asia/Shanghai`）**：数据库使用 naive `DateTime` 列存储 UTC+8 本地时间（`BaseModel` 默认 `now_cn`）；接口需返回可直接展示的时间时，使用 `to_cn_time(...)` 格式化为 `YYYY-MM-DD HH:MM:SS`（如 `2026-11-09 14:30:00`），不混用 `DateTime(timezone=True)`、裸 ISO 字符串或时间戳。

### 3. 统一响应与全局异常处理
- 所有接口响应顶层始终包含 `code`（`0` 成功 / `1` 失败）、`message`、`data`；具体错误语义由 HTTP 状态码承载，失败时 `data` 保留为 `null`，错误明细放在独立的 `details` 字段，不塞入 `data`。
- 视图层一律调用 [references/responses.md](references/responses.md) 的 `success()` / `fail()` / `paginate()`，业务错误统一抛出 `APIException` 或其子类，由 [references/exceptions.md](references/exceptions.md) 中的 `register_error_handlers(app)` 和 `register_jwt_error_handlers(jwt)` 统一收口（含 Pydantic `ValidationError`、Werkzeug `HTTPException` 与 JWT 认证错误）。

### 4. 日志与生产部署
- 采用 [references/logger.md](references/logger.md) 中的 Loguru 拦截桥接方案（`enqueue=True` 保证多进程写安全），遵循 `app.config["LOG_LEVEL"]` 与 `app.config["LOG_PATH"]`。
- Web 进程写入 `web.log`，独立调度进程写入 `scheduler.log`，避免混写导致排障困难。
- 生产环境使用 Gunicorn 与 [references/gunicorn-config.md](references/gunicorn-config.md) 的配置模板（`gunicorn "wsgi:app" -c gunicorn.conf.py`）。

### 5. 路由、入口与代码质量
- 使用原生 `Blueprint` 按业务拆分路由，通过 `app/api/__init__.py` 的 `register_blueprints(app)` 集中注册；蓝图模块顶层不执行数据库查询或网络请求等副作用。
- `wsgi.py` 仅调用 `create_app()` 暴露 `app`；`manage.py` 保持极简，仅实例化 `app` 并 `app.run()`，不引入自定义 Click 子命令（迁移继续走原生 `flask db`）。
- 单函数控制在 100 行以内、单文件控制在 600 行以内，超出时及时拆分私有方法或子模块。

### 6. 独立调度进程（仅项目需要定时任务时）
- 使用 `BlockingScheduler` + `SQLAlchemyJobStore`（持久化到 PostgreSQL `apscheduler_jobs` 表，包含 `next_run_time` 索引，通过手工迁移创建，见 [references/migrate.md](references/migrate.md)）。
- 绝不在 Flask Web 进程内启动调度器；Web 与 `scripts/run_scheduler.py` 共享同一份 `.env`、`config.py` 和 `app/tasks/` 任务代码。
- 调度开关、频率参数由数据库驱动，每次执行结果（状态、耗时、错误摘要）落库审计并保留近 1 个月。详见 [references/scheduler-architecture.md](references/scheduler-architecture.md) 与 [references/scheduler-api.md](references/scheduler-api.md)。

## 环境管理与文档约定

使用 `uv` 作为唯一依赖与环境入口（仅在旧项目明确要求兼容时才保留 `requirements.txt`）：

```bash
uv python pin 3.12
uv sync
```

项目文档按需维护在 `docs/`：
- `docs/api.md`：统一响应/错误格式、状态码约定；（启用调度器时）补充任务管理端点、数据库驱动参数与并发/幂等保护策略。
- `docs/development.md`：`uv` 初始化、`flask db` 迁移、Web 服务启动及（如有）独立调度进程与日志排查方式。
- `docs/architecture.md`：分层说明及（如有）Web 与 `scripts/run_scheduler.py` 解耦架构、共享 `app/tasks/` 组织方式。

## 测试规范

> 初始生成脚手架时仅预留 `tests/` 目录结构；当用户要求编写测试或核心业务稳定后，按以下约束实现。

- 使用 `pytest` + Flask `test_client`，在 `tests/conftest.py` 提供共享 fixtures（`app`、`client`、`db_session`）。
- 测试库必须通过 `TEST_DATABASE_URL` 与开发/生产库物理隔离，并在 session fixture 中调用 `flask_migrate.upgrade()` 同步表结构（见 [references/migrate.md](references/migrate.md)）。
- 每个用例独立可重入，测试结束后回滚事务或清理数据，同时校验 HTTP 状态码与返回体 `code`（`0`/`1`）。

## 交付自检清单 (Review Checklist)

- [ ] `app/__init__.py` 提供 `create_app()`，配置动态加载 `.env`，生产/测试环境均经过 `validate()` 校验，无硬编码密钥。
- [ ] 使用 `uv`（`pyproject.toml` / `uv.lock` / `.python-version`）与 `postgresql+psycopg://`；所有建表走 Flask-Migrate，无 `db.create_all()`。
- [ ] 模型继承 `BaseModel`、采用 SQLAlchemy 2.0 `Mapped[...]`、物理列有 `comment` 且 `relationship()` 无 `comment`、时间全链路 UTC+8。
- [ ] 查询统一使用 `db.session.query(...)`（无 `Model.query`）；视图层不手写散装 JSON，也不在视图中裸写多步 `commit()`。
- [ ] 全局异常处理器覆盖 `APIException`、`ValidationError`、`HTTPException`、`Exception` 及（如有）JWT 错误，统一返回 `code/message/data`。
- [ ] Loguru 日志尊重 `LOG_LEVEL` / `LOG_PATH`，Web 与调度日志分离。
- [ ] 若启用调度器：仅由 `scripts/run_scheduler.py` 启动 `BlockingScheduler`，`apscheduler_jobs` 有对应迁移脚本，任务执行记录落库。
