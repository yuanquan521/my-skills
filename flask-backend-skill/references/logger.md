# Logging Template (Loguru)

针对 Flask + 多进程运行场景（如 Gunicorn / APScheduler），使用 `loguru` 统一接管标准 `logging` 输出并桥接 Flask 的 `app.logger`。

通过 `enqueue=True` 保证多进程并发写日志不错乱，同时读取 `app.config["LOG_LEVEL"]` 与 `app.config["LOG_PATH"]`，确保 `.env` 配置实际生效且 Web / 调度器日志落盘分离。

## Logger 配置示例 (`app/extensions/logger.py`)

```python
import logging
import os
import sys
from flask import Flask
from loguru import logger


class InterceptHandler(logging.Handler):
    """统一接管标准 logging 日志并转发给 loguru。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging(app: Flask, is_scheduler: bool = False) -> None:
    """
    配置全局日志并接管 app.logger。
    :param app: Flask 实例（需先加载 config）
    :param is_scheduler: True 写入 scheduler.log，False 写入 web.log
    """
    log_level = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    base_log_dir = app.config.get("LOG_PATH", "logs")
    os.makedirs(base_log_dir, exist_ok=True)

    logger.remove()

    # 1. 控制台输出
    logger.add(
        sys.stdout,
        enqueue=True,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # 2. 按进程分离日志文件（Web 与 Scheduler 不混写）
    log_file = "scheduler.log" if is_scheduler else "web.log"
    log_path = os.path.join(base_log_dir, log_file)
    logger.add(
        log_path,
        rotation="00:00",
        retention="30 days",
        enqueue=True,
        level=log_level,
        encoding="utf-8",
    )

    # 3. 将标准 logging 重定向到 loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for _log in ("werkzeug", "gunicorn.error", "gunicorn.access", "apscheduler"):
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False

    # 4. 接管 Flask 自带的 app.logger
    app.logger.handlers = [InterceptHandler()]
    app.logger.propagate = False
```

## 使用说明

### 1. Web 进程入口 (`app/__init__.py`)

在 `create_app()` 加载配置之后调用：

```python
from flask import Flask
from config import load_config
from app.extensions.logger import configure_logging


def create_app(env: str | None = None, *, is_scheduler: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(load_config(env))
    configure_logging(app, is_scheduler=is_scheduler)
    # ... 初始化数据库、扩展、异常处理器与蓝图
    return app
```

在蓝图或异常处理器中调用 `current_app.logger.info(...)` / `current_app.logger.exception(...)`，都会自动走 Loguru 排版与安全入队。

### 2. 独立调度进程 (`scripts/run_scheduler.py`)

传入 `is_scheduler=True`，避免调度进程先初始化一次 `web.log` 再切换：

```python
from app import create_app

app = create_app(is_scheduler=True)
```
