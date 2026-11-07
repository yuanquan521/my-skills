---
name: flask-backend-skill
description: Generate a pure Flask backend API project in the current directory with app factory, PostgreSQL, Flask-SQLAlchemy, psycopg3, JWT, Pydantic, Loguru, optional Redis, and a standalone APScheduler process sharing Flask config and task code.
allowed-tools: Read Write Edit MultiEdit Glob Grep Bash
compatibility: Requires Python 3.12+, PostgreSQL, and uv package manager. Compatible with Claude Code and OpenCode.
---

# Flask Backend API Skill

## Purpose

在当前已存在项目目录中，生成一个纯后端 Flask API 项目，并满足统一分层、统一返回格式、统一异常处理、独立调度进程、数据库驱动调度参数和任务执行审计等约束。

## When To Use

- 需要标准化 Flask 后端接口项目
- 需要工厂模式 + `.env` 配置分层
- 需要 PostgreSQL + Flask-SQLAlchemy + psycopg3
- 需要 Flask-JWT-Extended + Pydantic + Loguru + 可选 Redis
- 需要独立调度进程（APScheduler），与 Flask 共享配置与任务代码
- 需要统一响应结构 `code/message/data`

## Non-Goals

- 不生成前端页面
- 不要求创建项目目录、复制模板仓库或手工搬运模板

## Required Stack

### Core

- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- python-dotenv

### Database

- PostgreSQL
- psycopg3的安装注意包名是 psycopg, uv安装为：uv add "psycopg[binary]"
- 连接串必须为 `postgresql+psycopg://`

### Auth

- Flask-JWT-Extended
- JWT `identity` 只存用户 ID
- JWT 算法固定 `HS256`
- `JWT_COOKIE_SECURE` 默认开启

### Validation / Logging

- Pydantic
- Loguru（多进程安全能力）

### Optional

- Redis（按开关加载）

### Scheduler

- APScheduler（使用 `BlockingScheduler`）
- SQLAlchemyJobStore（任务调度状态持久化到 PostgreSQL）
- 禁止使用 Flask-APScheduler

### Server

- 生产环境使用 Gunicorn，配置文件为 `gunicorn.conf.py`
- **强制配置约束**：必须原样使用 [Gunicorn 配置参考](references/gunicorn-config.md) 提供的配置文件模板和启动命令。

## Project Layout

```text
my_flask_project/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── config.py
├── manage.py
├── wsgi.py
├── gunicorn.conf.py
├── migrations/              # Flask-Migrate 生成，必须纳入 Git
├── docs/
├── scripts/
│   └── run_scheduler.py
├── tests/
└── app/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── exceptions.py
    │   ├── responses.py
    │   ├── security.py
    │   └── utils/
    │       ├── __init__.py
    │       └── helpers.py
    ├── extensions/
    │   ├── __init__.py
    │   ├── database.py
    │   ├── logger.py
    │   ├── auth.py
    │   └── server.py
    ├── models/
    │   ├── __init__.py
    │   ├── user.py
    │   ├── scheduled_task.py
    │   └── task_execution_record.py
    ├── schemas/
    │   ├── __init__.py
    │   ├── base.py
    │   └── user.py
    ├── scheduler/
    │   ├── __init__.py
    │   ├── manager.py
    │   ├── loader.py
    │   └── runner.py
    ├── tasks/
    │   ├── __init__.py
    │   ├── registry.py
    │   └── jobs/
    │       ├── __init__.py
    │       └── ...
    └── api/
        ├── __init__.py
        ├── auth.py
        ├── users.py
        └── tasks.py
```

## Core Constraints

### Factory Pattern

- `app/__init__.py` 必须提供 `create_app()`
- 必须根据根目录 `.env` + 环境变量加载 `DevelopmentConfig` / `TestingConfig` / `ProductionConfig`
- 扩展初始化必须集中管理
- **强制配置分层约束**：必须严格基于 [配置管理参考](references/config.md) 中的模板代码来实现配置类和环境变量的管理。

### Config Management

- 必须生成 `.env.example`
- 必须覆盖数据库、JWT、Redis、日志、调度相关配置项
- 生产与开发配置分离
- 密钥禁止硬编码

### Database

- **强制使用 Flask-Migrate**（Alembic）管理所有数据库 Schema 变更，禁止使用 `db.create_all()`
- `migrate` 实例必须在 `app/extensions/database.py` 中与 `db` 一同声明，并在工厂函数中调用 `migrate.init_app(app, db)`
- 每次模型变更后必须执行 `flask db migrate -m "描述"` 生成迁移脚本，并人工审查后再执行 `flask db upgrade`
- `migrations/` 目录必须纳入版本控制
- **强制迁移规约**：必须严格遵守 [数据库迁移参考](references/migrate.md) 中说明的初始化方式和约束规则。
- 生产连接池配置必须独立
- **强制模型基类约束**：必须严格拷贝并继承 [模型基类参考](references/models.md) 中提供的 `BaseModel` 模板。
- **强制模型注解约束**：必须使用 SQLAlchemy 2.0 现代写法（类似 `Mapped[str] = mapped_column(...)`）做类型注解。
- **强制模型注释约束**：所有物理表字段映射中，必须使用 `comment="说明"` 添加注释；但在外键或关联（`relationship()`）声明中**绝对禁止**使用 `comment`。
- **强制查询语法约束**：查询结构时，强制使用 `db.session.query(Model).filter_by(...)` 的语法进行查询。

### Logging

- Web 日志与调度器日志必须分离
- 调度器必须写入独立日志文件（例如 `logs/scheduler.log`）
- **强制日志配置约束**：必须严格拷贝并使用 [日志模块模板](references/logger.md) 中的 Loguru 拦截与 Flask `app.logger` 桥接机制代码。

### Code Quality

- 单个函数代码行数强制不得超过 100 行（提倡提前 Return 和抽离私有方法）
- 单个源文件代码行数强制不得超过 600 行（遇超长文件需即刻进行模块/蓝图的原子拆分）

## Unified Response And Exception Rules

### Required Response Shape

所有接口返回体顶层必须始终包含：

- `code`：业务码，`0` 表示成功，`1` 表示失败
- `message`：提示信息
- `data`：业务数据

约束：

- 成功和失败响应都不能缺失以上字段
- 错误语义由 HTTP 状态码承载（如 `400` / `401` / `404` / `500` 等），`code` 仅区分成功与失败
- 失败响应中 `data` 必须保留且建议为 `null`
- 错误详情对象不能放在 `data` 中
- 错误详情需放独立字段（如 `details` / `errors`）

### Response / Exception Management

- **强制响应格式约束**：必须严格按照 [响应封装模板](references/responses.md) 中的代码作为 `app/core/responses.py`。
- **强制异常处理约束**：业务抛错与全局异常捕获**必须严格原样使用** [异常处理模板](references/exceptions.md) 中的全部代码作为 `app/core/exceptions.py`。工厂函数必须调用 `register_error_handlers(app)`，并在 `JWTManager` 初始化后调用 `register_jwt_error_handlers(jwt)`，确保 Pydantic 与 JWT 错误也使用统一响应。
- 统一 HTTP 状态码与业务错误码映射。遇到业务错误，**一律通过** `raise APIException(...)` 或其子类来中止请求并抛出，交给全局拦截器处理。
- 视图层禁止手写零散拼装的返回结构。

## Scheduler Architecture (Rewritten)

### Absolute Rules

- 使用 APScheduler，不使用 Flask-APScheduler
- 使用 `BlockingScheduler` 作为独立调度进程
- 禁止在 Flask Web App 进程内启动调度器
- Flask 与调度器必须共享同一套配置来源（同一个 `.env` 与 `config.py`）

### Shared Code Model

- `app/tasks/` 是 Flask 与调度进程共享的公共任务仓库
- Flask API 可以手动触发 `app/tasks/` 中任务
- 独立调度进程按计划定时触发同一批任务

Detailed constraints on scheduler management, DB-driven parameters, execution records, and signal handling: see [scheduler architecture details](references/scheduler-architecture.md).

## Scheduler API Requirements (Flask Side)

Flask 侧必须提供任务管理 API（需鉴权），包括：手动触发、状态查询、配置修改、历史记录查询。

详细的端点设计、安全要求和注意事项见 [调度器 API 接口规范](references/scheduler-api.md)。

## Routing Rules

- 必须使用 Flask 原生的 `Blueprint` 划分模块
- 根据业务拆分不同的 Blueprint，使用函数视图直接绑定路由
- 所有 Blueprint 必须通过函数集中注册到 `app` 对象（在 `app/api/__init__.py` 中统一管理，比如对外暴露 `register_blueprints`）
- `auth` / `users` / `tasks` 业务模块的路由必须解耦独立

## Documentation Rules

### docs/api.md 必须说明

- 统一返回结构与错误结构
- 统一状态码/错误码
- 手动任务触发、状态查询、历史查询、配置修改接口
- 调度参数来自数据库的约束
- SQLAlchemyJobStore 持久化调度状态（不含 `next_run_time`）
- 写接口幂等与并发触发保护策略

### docs/development.md 必须说明

- 使用 `uv` 初始化环境与安装依赖
- 如何启动 Web 服务
- 如何单独启动调度进程
- 调度日志与执行记录查看方式

### docs/architecture.md 必须说明

- Web 进程与调度进程解耦架构,在scripts/run_scheduler.py中启动和停止调度服务
- 共享 `app/tasks/` 的代码组织方式
- 调度配置与执行记录的数据库模型关系

## Entry Points

- `wsgi.py`：生产入口，仅负责调用 `create_app()` 并暴露 `app` 对象供 Gunicorn 加载（`gunicorn "wsgi:app"`）
- `manage.py`：开发启动脚本。要求代码极致简单，实例化 app 后直接调用 `app.run()` 启动服务器即可，**不需要依赖任何 CLI 命令行参数**。不要使用 Click 或 Flask CLI 定义复杂的启动子命令。数据库迁移等仍使用项目内原生 `flask db` 命令即可。

## Environment Setup

默认前提：用户已创建并进入目标项目目录。

只保留环境与依赖步骤：

```bash
uv python install 3.12
uv venv --python 3.12
uv sync
```

如使用 `requirements.txt`：

```bash
uv pip install -r requirements.txt
```

## Testing Rules

> 初始生成项目脚手架时**不编写测试代码**，仅预留 `tests/` 目录结构。待核心业务逻辑稳定后再补充测试。

### 目录结构

```text
tests/
├── conftest.py          # pytest fixtures（app 实例、测试客户端、数据库会话等）
├── test_auth.py
├── test_users.py
└── test_tasks.py
```

### 约束

- 测试框架使用 `pytest`
- 必须通过 `conftest.py` 提供共享 fixtures（`app`、`client`、`db_session`）
- 测试数据库必须与开发/生产数据库隔离（推荐使用独立的 `_test` 后缀数据库）
- 每个测试用例必须具备独立性，不依赖其他用例的执行顺序或副作用
- API 测试使用 Flask 自带的 `test_client`，验证 HTTP 状态码与返回体中的 `code`（`0`/`1`）
- 涉及数据库的测试必须在测试结束后回滚或清理数据

## Anti-Patterns

- 不要在 Web App 内调用调度器启动
- 不要把调度频率和任务参数硬编码在代码里
- 不要把任务成功/失败只写日志不落库
- 不要把 Web 与调度器混为同一进程职责
- 不要把错误详情放进 `data`
- 不要在视图函数中直接操作 `db.session.commit()`（应封装到 Service 层或 Model 方法中）
- 不要在蓝图模块文件顶层执行有副作用的代码（如数据库查询、网络请求）
- 不要使用老旧的 `Model.query` 查询方式，强制使用 `db.session.query(Model).filter_by(...)` 的规范写法

## References Index

| 文件 | 说明 |
|------|------|
| [config.md](references/config.md) | 配置分层模板与 `.env.example` |
| [migrate.md](references/migrate.md) | Flask-Migrate 数据库迁移强制规范与命令用法 |
| [models.md](references/models.md) | 数据库 BaseModel 基类模板 |
| [exceptions.md](references/exceptions.md) | 统一异常类与全局错误捕获 |
| [responses.md](references/responses.md) | 统一响应封装（success/fail/paginate） |
| [logger.md](references/logger.md) | Loguru 日志配置与 Flask 桥接 |

| [gunicorn-config.md](references/gunicorn-config.md) | Gunicorn 生产配置文件模板 |
| [scheduler-architecture.md](references/scheduler-architecture.md) | 调度器架构详细约束 |
| [scheduler-api.md](references/scheduler-api.md) | 调度器 API 接口规范 |
