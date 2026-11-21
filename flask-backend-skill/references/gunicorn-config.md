# Gunicorn 生产配置参考

使用 `gthread`（多进程 + 多线程）适配 I/O 密集型 Flask + PostgreSQL API 场景。

> **关于日志去重**：应用侧 `app/extensions/logger.py` 已通过 Loguru 统一接管 `gunicorn.error` / `gunicorn.access` 并落盘至 `logs/web.log`。因此 Gunicorn 默认将 `accesslog` / `errorlog` 指向标准输出/错误（`"-"`），避免同时再写入一套重复的 `access.log` / `error.log`。如运维要求 Nginx 风格的独立访问日志文件，可通过 `GUNICORN_ACCESS_LOG` 环境变量显式开启。

## 配置文件示例 (`gunicorn.conf.py`)

```python
# gunicorn.conf.py
import multiprocessing
import os

# ============================================================
# Server Socket
# ============================================================
bind = os.getenv("GUNICORN_BIND", "127.0.0.1:9000")

# ============================================================
# Worker Processes
# ============================================================
# 工作模式（Worker Class）：
# - 'gthread'：多进程 + 多线程，适合 Flask 常见的数据库/外部 HTTP I/O 密集型接口（推荐）
# - 'sync'：纯单线程同步模式（配置 threads > 1 时 Gunicorn 会自动切换为 gthread）
# - 'gevent'：协程模式（需安装 gevent，适合超高并发长连接）
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.getenv("GUNICORN_THREADS", "2"))

# ============================================================
# Worker Lifecycle
# ============================================================
timeout = 120                      # Worker 响应超时（秒）
graceful_timeout = 30              # 优雅停机等待时间（秒）
keepalive = 5                      # Keep-Alive 连接超时（秒）
max_requests = 1000                # 单 Worker 处理最大请求数后重启（防内存泄漏）
max_requests_jitter = 200          # 抖动值，避免所有 Worker 同时重启

# ============================================================
# Security
# ============================================================
limit_request_line = 8190          # 请求行最大长度
limit_request_fields = 100         # 请求头最大字段数
limit_request_field_size = 8190    # 单个请求头字段最大长度

# ============================================================
# Process Naming
# ============================================================
proc_name = os.getenv("GUNICORN_PROC_NAME", "flask_app")

# ============================================================
# Logging
# ============================================================
# 默认输出到 stdout/stderr，配合容器日志采集或 Loguru web.log，避免双份落盘；
# 若需独立文件可设置 GUNICORN_ACCESS_LOG=logs/access.log。
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# ============================================================
# Server Hooks（可选，按需启用）
# ============================================================
def on_starting(server):
    """服务启动前回调"""
    pass


def post_fork(server, worker):
    """Worker fork 后回调（若 preload_app=True，需在此处清理父进程数据库连接池）"""
    pass


def worker_exit(server, worker):
    """Worker 退出回调，适合清理资源"""
    pass
```

## 启动命令

```bash
# 开发环境
uv run gunicorn "wsgi:app" -c gunicorn.conf.py --reload

# 生产环境
uv run gunicorn "wsgi:app" -c gunicorn.conf.py
```
