# 调度器架构详细约束与参考模板

仅在项目需要后台定时任务时启用本模块。Web 进程与调度进程解耦，避免 Gunicorn 多 Worker 启动多份调度器造成任务重复执行。

## 核心架构约束

- 调度任务定义与元数据由数据库驱动，通过 `app/scheduler/`（`manager.py` / `loader.py` / `runner.py`）统一管理。
- 使用 `BlockingScheduler` + `SQLAlchemyJobStore`（持久化到 PostgreSQL `apscheduler_jobs` 表）。
- `apscheduler_jobs` 不属于 Flask-SQLAlchemy 模型 metadata，必须通过 [Flask-Migrate 参考](migrate.md#apscheduler-job-store-建表迁移) 中的手工迁移创建，并在启动调度器前执行 `flask db upgrade`。
- 调度状态至少可追踪：任务是否启用、trigger 信息、`next_run_time`（由 `apscheduler_jobs` 持久化）。
- 保证单调度器实例运行，不并发启动多个共享同一 jobstore 的调度进程。
- 任务可调用目标必须是可导入的模块级函数（如 `app.tasks.jobs.sync:run_sync`），禁止使用匿名函数或闭包。

## 数据库驱动参数

以下参数从数据库（`scheduled_tasks` 表）读取，不硬编码在代码中：

- 任务启停状态（`enabled`）
- 调度类型与频率（`trigger_type`: `interval` / `cron` / `date` 及实际参数）
- 业务执行参数（JSON）
- 重试与超时策略（如业务需要）
- 最近执行时间、配置版本号与更新时间（用于调度器检测并重载变更）

## 执行审计记录

每次任务执行（包括定时触发与 API 手动触发）都必须落库到 `task_execution_records`：

- 任务 ID、触发来源（`scheduled` / `manual`）
- 开始时间 / 结束时间（UTC+8，使用 `now_cn`）
- 执行状态（`success` / `failed`）
- 错误信息摘要（失败时）
- 关键执行上下文（脱敏）
- 定期清理策略：仅保留最近 1 个月的执行记录

## 独立调度进程入口模板 (`scripts/run_scheduler.py`)

```python
#!/usr/bin/env python3
"""独立 APScheduler 调度进程入口：与 Flask Web 共享配置和 app/tasks/ 代码。"""

import signal
import sys

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.blocking import BlockingScheduler

from app import create_app


def build_scheduler(database_url: str) -> BlockingScheduler:
    jobstores = {
        "default": SQLAlchemyJobStore(url=database_url, tablename="apscheduler_jobs")
    }
    return BlockingScheduler(
        jobstores=jobstores,
        timezone="Asia/Shanghai",
        job_defaults={"coalesce": True, "max_instances": 1},
    )


def main() -> None:
    app = create_app(is_scheduler=True)
    if not app.config.get("SCHEDULER_ENABLED", False):
        app.logger.warning("SCHEDULER_ENABLED 未开启，调度进程退出")
        return

    scheduler = build_scheduler(app.config["SQLALCHEMY_DATABASE_URI"])

    def handle_shutdown(signum, _frame):
        app.logger.info(f"收到退出信号 ({signum})，等待当前任务完成后优雅停止调度器...")
        # shutdown(wait=True) 会停止新调度并等待正在执行的任务收尾
        scheduler.shutdown(wait=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    with app.app_context():
        # 从数据库加载启用的任务配置并同步到 scheduler（实现位于 app/scheduler/loader.py）
        from app.scheduler.loader import sync_jobs_from_db

        sync_jobs_from_db(scheduler)
        app.logger.info("独立调度进程已启动")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            app.logger.info("调度进程已停止")


if __name__ == "__main__":
    main()
```

> **注意**：`app/scheduler/runner.py` 包装具体任务函数时，应在执行前创建/进入 `app.app_context()`，捕获异常并写入 `task_execution_records`，避免单次任务异常导致调度线程静默丢失审计记录。
