# Logging Template (Loguru)

针对 Flask + 多进程运行场景（如 Gunicorn / APScheduler），使用 `loguru` 统一接管所有的标准 `logging` 输出，并覆盖 Flask 内部默认的 `app.logger`。

这样可以彻底解决多进程并发写日志的资源冲突（利用 `enqueue=True`），并让无论是业务直接抛出的日志、Werkzeug 访问日志还是调度系统自带的事件日志格式完全统一。

## Logger 配置示例 (`app/extensions/logger.py`)

```python
import logging
import sys
import os
from loguru import logger
from flask import Flask

class InterceptHandler(logging.Handler):
    """
    统一接管标准 logging 日志，转发给 loguru。
    解决 Gunicorn、Flask 等多处系统及框架本身采用不同日志器发生输出错乱的问题。
    """
    def emit(self, record):
        # 尝试获取对应 loguru 的级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到调用者所在的帧，避免日志的模块名错误显示为 InterceptHandler 内
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def configure_logging(app: Flask, is_scheduler: bool = False):
    """
    配置全局日志。
    :param app: 传入 Flask 实例以读取配置并彻底接管 app.logger
    :param is_scheduler: 用于决定分开存放日志路径
    """

    # 清除 loguru 默认的 handler
    logger.remove()

    # 1. 控制台输出
    logger.add(
        sys.stdout,
        enqueue=True, # 开启多进程/多线程安全队列
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # 2. 根据不同进程切分文件 (务必分离 Web 日志与 Scheduler 日志)
    # 日志文件的目录来源于 Flask config 中的 LOG_PATH
    base_log_dir = app.config.get("LOG_PATH", "logs")
    log_path = os.path.join(base_log_dir, "scheduler.log") if is_scheduler else os.path.join(base_log_dir, "web.log")

    logger.add(
        log_path,
        rotation="00:00",     # 每天午夜轮转
        retention="30 days",  # 保留30天
        enqueue=True,         # 多进程/多线程下安全的写锁机制
        level="INFO",
        encoding="utf-8"
    )

    # 3. 将标准 logging 重定向到 loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 彻底覆盖常见的系统级别日志器
    for _log in ['werkzeug', 'gunicorn.error', 'gunicorn.access', 'apscheduler']:
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False

    # 4. 接管 flask 的自带 app.logger
    app.logger.handlers = [InterceptHandler()]
    app.logger.propagate = False
```

## 使用说明

### 1. Web 进程入口使用

在你的 `app/__init__.py` 工厂函数中，或者 `wsgi.py` 最顶层入口处：

```python
from app.extensions.logger import configure_logging
from flask import Flask

def create_app():
    app = Flask(__name__)

    # 配置并彻底接管 Web 端日志
    configure_logging(app, is_scheduler=False)

    ...
    return app
```

随后你在任意 `blueprint` 或者 `exceptions.py` 里调用 `current_app.logger.exception(...)` 或 `current_app.logger.info(...)` 时，底层其实生效的已经是带有漂亮排版以及安全入队的 Loguru 引擎了。

### 2. 独立调起的调度进程使用

在你的独立调度进程文件如 `scripts/run_scheduler.py` 内部开头：

```python
from app.extensions.logger import configure_logging
from app import create_app

# 调度器也需要依托 Flask 应用上下文以共享配置和操作数据库
app = create_app()

# 接管独立的调度器日志
configure_logging(app, is_scheduler=True)

with app.app_context():
    # ... 继续实例化 APScheduler 及读取配置等
```
