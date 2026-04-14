# 调度器架构详细约束

## Dedicated Scheduler Management

- 调度任务定义与元数据由数据库驱动
- 必须有独立的任务管理模型与服务层（`app/scheduler/`）
- 调度器加载器必须从数据库拉取任务配置并动态注册
- 必须使用 SQLAlchemyJobStore，将调度状态持久化到 PostgreSQL
- 必须明确使用独立 job store 表（默认 `apscheduler_jobs` 或等价配置）
- 调度状态至少应可追踪：任务是否启用、trigger 信息、`next_run_time`
- 调度进程实例之间不得并发共享同一 jobstore 进行重复调度（必须保证单调度器实例）
- 任务可调用目标必须为可导入的模块级函数，禁止使用匿名函数/闭包作为持久化任务入口

## DB-Driven Parameters (Mandatory)

以下参数必须从数据库读取，禁止硬编码在调度代码中：

- 任务启停状态
- 调度类型与频率（如 interval/cron/date 的实际参数）
- 执行间隔或 Cron 表达式
- 任务执行所需业务参数
- 重试策略、超时策略（如项目有定义）
- 任务最近执行时间、下次执行时间（或可推导字段）
- 任务配置版本号与更新时间（用于调度器重载判定）

## Execution Record (Mandatory)

每次任务执行都必须落库：

- 任务 ID
- 开始时间 / 结束时间
- 执行状态（成功/失败）
- 错误信息摘要（失败时）
- 关键执行上下文（必要且脱敏）
- 数据库中的任务信息只保留最近1个月

## Process / Signal Handling

- 使用 `BlockingScheduler` 时必须处理 `SystemExit` 信号
- 在scripts/run_scheduler.py中启动和停止调度服务
- 服务重启或停止时，应尽量让正在执行的任务完整收尾
- 必须有可控的优雅停止策略（例如先停止新调度，再等待当前任务结束）
- 日志配置见 [日志模块模板](logger.md)，调度进程启动时需调用 `configure_logging(app, is_scheduler=True)`
