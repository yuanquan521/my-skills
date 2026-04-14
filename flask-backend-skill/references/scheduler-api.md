# 调度器 API 接口规范

## Scheduler API Requirements (Flask Side)

Flask 侧至少提供以下受控能力（需鉴权、建议管理员权限）：

- 任务手动触发接口
- 调度器运行状态查询接口
- 任务配置查看接口（读取数据库中的调度与执行参数）
- 任务调度配置修改接口（可更新间隔）
- 任务历史执行记录查询接口（成功/失败、耗时、错误摘要）

## Recommended Endpoint Shape

- `GET /api/tasks/schedules`：查询任务调度配置列表
- `GET /api/tasks/schedules/{task_id}`：查询单任务调度配置
- `PATCH /api/tasks/schedules/{task_id}`：更新调度配置（interval）
- `GET /api/tasks/status`：查询任务当前状态（含 `next_run_time`）
- `GET /api/tasks/status/{task_id}`：查询单任务状态详情
- `GET /api/tasks/history`：分页查询任务历史记录
- `GET /api/tasks/history/{task_id}`：查询单任务历史记录
- `POST /api/tasks/trigger/{task_id}`：手动触发任务

## API Safety Requirements

- 所有写接口（如 `PATCH`、`POST trigger`）必须具备幂等保护
- 手动触发前必须校验任务存在且可执行，避免并发重复触发
- 配置修改必须写入数据库并带版本/时间戳，便于调度进程识别变更
- 历史查询接口必须支持分页与时间范围过滤

## 说明

- 这些接口负责"管理与触发"，不代表在 Web 进程中内嵌启动调度器
- Web 侧如需控制调度进程，应采用进程外控制方案，不能在 Web 进程直接 `start()` 一个内嵌 scheduler
- 配置修改后必须有可追踪的一致性策略（如即时重载或下次调度生效策略）
- 手动触发接口必须记录执行结果到历史表
