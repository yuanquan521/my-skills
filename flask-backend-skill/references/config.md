# Config Template

工厂模式下的配置分层模板。所有配置从根目录 `.env` 与环境变量动态读取，禁止硬编码密钥。

> **为什么使用函数动态构建配置类而不是在模块 import 时求值？**
> 如果在类定义体里直接写 `SQLALCHEMY_DATABASE_URI = os.getenv(...)`，那么在 `pytest` 或脚本中只要先导入了 `config`，后续修改 `os.environ["FLASK_ENV"]` 或 `os.environ["TEST_DATABASE_URL"]` 都不会生效。通过 `load_config(env)` 在 `create_app()` 调用时即时读取环境变量，即可彻底消除这类隐蔽的状态泄漏。

## 配置模块示例 (`config.py`)

```python
import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _build_base_config() -> dict:
    secret_key = os.getenv("SECRET_KEY", "change-me-in-production")
    return {
        # ---- Security ----
        "SECRET_KEY": secret_key,
        # ---- Database ----
        "SQLALCHEMY_DATABASE_URI": os.getenv(
            "DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/mydb"
        ),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        # ---- JWT ----
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", secret_key),
        "JWT_ALGORITHM": "HS256",
        "JWT_ACCESS_TOKEN_EXPIRES": timedelta(
            hours=int(os.getenv("JWT_ACCESS_HOURS", "2"))
        ),
        "JWT_REFRESH_TOKEN_EXPIRES": timedelta(
            days=int(os.getenv("JWT_REFRESH_DAYS", "30"))
        ),
        "JWT_COOKIE_SECURE": True,
        # ---- Redis (optional) ----
        "REDIS_ENABLED": _env_bool("REDIS_ENABLED", False),
        "REDIS_HOST": os.getenv("REDIS_HOST", "127.0.0.1"),
        "REDIS_PORT": int(os.getenv("REDIS_PORT", "6379")),
        "REDIS_PWD": os.getenv("REDIS_PWD", ""),
        "REDIS_DB": int(os.getenv("REDIS_DB", "0")),
        # ---- Logging ----
        "LOG_PATH": os.getenv("LOG_PATH", "logs"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        # ---- Scheduler (optional) ----
        "SCHEDULER_ENABLED": _env_bool("SCHEDULER_ENABLED", False),
    }


class BaseConfig:
    """所有环境共享的基础配置基类（用于类型表达与 IDE 提示）。"""

    @classmethod
    def to_dict(cls) -> dict:
        return _build_base_config()

    @classmethod
    def validate(cls, cfg: dict) -> None:
        pass


class DevelopmentConfig(BaseConfig):
    """开发环境配置"""

    @classmethod
    def to_dict(cls) -> dict:
        cfg = super().to_dict()
        cfg.update(DEBUG=True, JWT_COOKIE_SECURE=False)
        return cfg


class TestingConfig(BaseConfig):
    """测试环境配置；必须显式使用与开发/生产不同的数据库"""

    @classmethod
    def to_dict(cls) -> dict:
        cfg = super().to_dict()
        cfg.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI=os.getenv("TEST_DATABASE_URL"),
            JWT_COOKIE_SECURE=False,
        )
        return cfg

    @classmethod
    def validate(cls, cfg: dict) -> None:
        test_uri = cfg.get("SQLALCHEMY_DATABASE_URI")
        default_uri = os.getenv("DATABASE_URL")
        if not test_uri:
            raise RuntimeError("测试环境必须配置 TEST_DATABASE_URL")
        if default_uri and test_uri == default_uri:
            raise RuntimeError("TEST_DATABASE_URL 必须与 DATABASE_URL 指向不同数据库")


class ProductionConfig(BaseConfig):
    """生产环境配置；两个密钥都必须显式配置，禁止继承占位值或互相回退"""

    @classmethod
    def to_dict(cls) -> dict:
        cfg = super().to_dict()
        cfg.update(
            DEBUG=False,
            SECRET_KEY=os.getenv("SECRET_KEY"),
            JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY"),
            SQLALCHEMY_ENGINE_OPTIONS={
                "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
                "pool_pre_ping": True,
                "pool_recycle": 300,
            },
        )
        return cfg

    @classmethod
    def validate(cls, cfg: dict) -> None:
        placeholders = {
            "change-me-in-production",
            "your-secret-key-here",
            "your-jwt-secret-key",
        }
        for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
            value = cfg.get(key)
            if not value or value in placeholders:
                raise RuntimeError(f"生产环境必须配置非占位 {key}")


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def load_config(env: str | None = None) -> dict:
    """在 create_app() 调用时加载 .env 并返回校验后的配置字典。"""
    load_dotenv(os.path.join(basedir, ".env"), override=False)
    resolved_env = (env or os.getenv("FLASK_ENV", "development")).strip().lower()
    config_class = config_map.get(resolved_env)
    if config_class is None:
        raise RuntimeError(f"不支持的 FLASK_ENV: {resolved_env}")
    cfg = config_class.to_dict()
    config_class.validate(cfg)
    return cfg
```

## `.env.example` 模板

```bash
# ============ App ============
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# ============ Database ============
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/mydb
# 测试必须显式使用独立数据库，pytest 不会回退到 DATABASE_URL
TEST_DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/mydb_test
# DB_POOL_SIZE=10
# DB_MAX_OVERFLOW=20

# ============ JWT (optional) ============
JWT_SECRET_KEY=your-jwt-secret-key
# JWT_ACCESS_HOURS=2
# JWT_REFRESH_DAYS=30

# ============ Redis (optional) ============
REDIS_ENABLED=false
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PWD=
REDIS_DB=0

# ============ Logging ============
LOG_PATH=logs
LOG_LEVEL=INFO

# ============ Scheduler (optional) ============
SCHEDULER_ENABLED=false

# ============ Gunicorn ============
GUNICORN_BIND=127.0.0.1:9000
# GUNICORN_WORKERS=5
# GUNICORN_THREADS=2
```

## 工厂函数中的用法

```python
from flask import Flask
from config import load_config


def create_app(env: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(load_config(env))

    # ... 初始化日志、扩展、注册异常处理器与蓝图
    return app
```
