# Gunicorn 生产配置参考

## 配置文件示例

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
# - 'sync'：默认的同步模式，适合CPU密集型
# - 'gevent' 或 'eventlet'：适合IO密集型（如大量的外部请求、数据库读写）
# - 'uvicorn.workers.UvicornWorker'：如果你运行的是 FastAPI 或其他 ASGI 应用
worker_class = "sync"          # 线程模式，适合 I/O 密集型
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.getenv("GUNICORN_THREADS", "2"))
worker_connections = 1000

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
proc_name = "flask_app"            # 进程名，方便 ps/top 识别

# ============================================================
# Logging
# ============================================================
GUNICORN_LOG = os.getenv("LOG_PATH", "logs")
os.makedirs(GUNICORN_LOG, exist_ok=True)   # 日志目录不存在则自动创建
accesslog = os.path.join(GUNICORN_LOG, "access.log")
errorlog = os.path.join(GUNICORN_LOG, "error.log")
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# ============================================================
# Server Hooks（可选，按需启用）
# ============================================================
def on_starting(server):
    """服务启动前回调"""
    pass

def post_fork(server, worker):
    """Worker fork 后回调，适合重新初始化数据库连接等"""
    pass

def worker_exit(server, worker):
    """Worker 退出回调，适合清理资源"""
    pass
```

## 启动命令

```bash
# 开发环境
gunicorn "wsgi:app" -c gunicorn.conf.py --reload

# 生产环境
gunicorn "wsgi:app" -c gunicorn.conf.py
```
