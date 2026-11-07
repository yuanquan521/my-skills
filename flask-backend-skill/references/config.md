# Config Template

工厂模式下的配置分层模板。所有配置从 `.env` 读取，禁止硬编码密钥。

## 配置类示例 (`config.py`)

```python
import os
from datetime import timedelta
from dotenv import load_dotenv

# 优先加载项目根目录的 .env 文件
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class BaseConfig:
    """所有环境共享的基础配置"""

    # ---- Security ----
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

    # ---- Database ----
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/mydb"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- JWT ----
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_ACCESS_HOURS", "2"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_DAYS", "30"))
    )
    JWT_COOKIE_SECURE = True

    # ---- Redis (optional) ----
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
    REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PWD = os.getenv("REDIS_PWD", "")
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))

    # ---- Logging ----
    LOG_PATH = os.getenv("LOG_PATH", "logs")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # ---- Scheduler ----
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"




class DevelopmentConfig(BaseConfig):
    """开发环境配置"""
    DEBUG = True
    JWT_COOKIE_SECURE = False


class TestingConfig(BaseConfig):
    """测试环境配置；必须显式使用与当前开发/生产配置不同的数据库"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL")
    JWT_COOKIE_SECURE = False

    @classmethod
    def validate(cls):
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError("测试环境必须配置 TEST_DATABASE_URL")
        if cls.SQLALCHEMY_DATABASE_URI == BaseConfig.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError("TEST_DATABASE_URL 必须与 DATABASE_URL 指向不同数据库")


class ProductionConfig(BaseConfig):
    """生产环境配置；两个密钥都必须显式配置，禁止继承占位值或互相回退"""

    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    @classmethod
    def validate(cls):
        placeholders = {
            "change-me-in-production",
            "your-secret-key-here",
            "your-jwt-secret-key",
        }
        for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
            value = getattr(cls, key)
            if not value or value in placeholders:
                raise RuntimeError(f"生产环境必须配置非占位 {key}")

    # 生产连接池独立配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }




# 配置映射表，create_app() 根据 FLASK_ENV 环境变量选择
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
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

# ============ JWT ============
JWT_SECRET_KEY=your-jwt-secret-key
# JWT_ACCESS_HOURS=2
# JWT_REFRESH_DAYS=30

# ============ Redis ============
REDIS_ENABLED=false
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PWD=
REDIS_DB=0

# ============ Logging ============
LOG_PATH=logs
LOG_LEVEL=INFO

# ============ Scheduler ============
SCHEDULER_ENABLED=true



# ============ Gunicorn ============
GUNICORN_BIND=127.0.0.1:9000
# GUNICORN_WORKERS=5
# GUNICORN_THREADS=2
```

## 工厂函数中的用法

```python
from config import config_map

def create_app():
    app = Flask(__name__)

    env = os.getenv("FLASK_ENV", "development")
    config_class = config_map.get(env, config_map["development"])
    if env in {"production", "testing"}:
        config_class.validate()
    app.config.from_object(config_class)

    # ... 初始化扩展、注册蓝图等
    return app
```
