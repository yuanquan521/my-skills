# FastAPI 项目文件/模块组织方式调研

> 调研日期：2026-08-30。全部结论基于一手来源（官方文档、模板仓库与生产仓库在 GitHub 上的真实文件树与源码，通过 GitHub API/raw 逐文件核对），不含二手博客转述。

## TL;DR

| 来源 | 组织方式 | 每个域/资源的文件数 | service/repository 层 |
|---|---|---|---|
| [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)（官方团队模板） | **按技术横切**：全局 `api/routes/`、全局 `crud.py`、全局 `models.py` | 每个 resource **1 个** route 文件；CRUD/model 全项目共享 2 个平铺文件 | 无 service、无 repository；route 直接写查询，仅 user 有 crud 函数 |
| [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)（社区最高星实践指南） | **按域竖切**：`src/<domain>/` 包 | 完整域 **8–9 个**文件（router/schemas/models/dependencies/service/constants/config/exceptions/utils），纯外部服务域约 6 个 | 有 `service.py`，**明确无 repository 层**；service 直接写 SQLAlchemy |
| [FastAPI 官方文档 Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) | **按技术横切**：`app/routers/<resource>.py` + `app/dependencies.py` | 每个 resource **1 个** router 文件；教程不涉及 models/crud 的拆分 | 不涉及；router 文件即全部逻辑 |
| [Netflix/dispatch](https://github.com/Netflix/dispatch)（大型生产单体，47 个域包） | **按域竖切**：`src/dispatch/<domain>/` | 最小 CRUD 域 **4 个**文件（config/models/service/views）；复杂域 10+ 文件并再拆子包 | 有 `service.py`（模块级函数，直接 `db_session.query()`），**无 repository 抽象** |

一句话：**没有一家一手来源推荐 repository 层；service 层只在"域逻辑被多处复用/足够复杂"时出现；文件粒度的主流是"每资源 1 个路由文件 + 少数几个共享/域内文件"，而不是 6+ 文件起步。**

---

## 1. fastapi/full-stack-fastapi-template（FastAPI 官方团队模板）

来源：<https://github.com/fastapi/full-stack-fastapi-template>（master 分支，最新 commit `486f054`，2026-08-28）。文件树取自 GitHub Git Trees API（`recursive=1`），以下为 `backend/` 下全部 Python 文件的真实清单：

```
backend/app/
├── __init__.py
├── alembic/                      # 迁移（env.py + versions/）
├── api/
│   ├── __init__.py
│   ├── deps.py                   # 全局依赖（SessionDep、CurrentUser 等）
│   ├── main.py                   # 聚合各 route 的 api_router
│   └── routes/
│       ├── __init__.py
│       ├── items.py              # ← items 资源：1 个文件
│       ├── login.py              # ← login：1 个文件
│       ├── private.py
│       ├── users.py              # ← users 资源：1 个文件
│       └── utils.py
├── core/
│   ├── __init__.py
│   ├── config.py                 # 全局 Settings
│   ├── db.py
│   └── security.py
├── crud.py                       # ← 全项目所有域的 CRUD，1 个平铺文件
├── initial_data.py
├── main.py
├── models.py                     # ← 全项目所有 SQLModel 模型 + Pydantic schema，1 个平铺文件
└── utils.py
```

（源：`https://api.github.com/repos/fastapi/full-stack-fastapi-template/git/trees/master?recursive=1`；目录页 <https://github.com/fastapi/full-stack-fastapi-template/tree/master/backend/app>）

### 关键事实

1. **每个 API resource = 1 个 route 文件**。`api/routes/` 下就是 `items.py`、`users.py`、`login.py`、`private.py`、`utils.py`，一资源一文件，没有 `user/` 子包，更没有每资源 schemas/models 文件。
2. **models 不按域拆**。`app/models.py` 是单个文件，同时装下 DB 模型和 Pydantic schema（SQLModel 一体化）。证据：`app/api/routes/items.py` 第 9 行 `from app.models import Item, ItemCreate, ItemPublic, ItemsPublic, ItemUpdate, Message`（<https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/api/routes/items.py>）。
3. **crud 也不按域拆**。`app/crud.py` 单文件装全部域的 CRUD 函数（`create_user` / `update_user` / `get_user_by_email` / `authenticate` / `create_item`…），且是模块级函数，不是类（<https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/crud.py>）。
4. **CRUD-only 资源连 crud 函数都不写**。`routes/items.py` 的 read/create/update/delete 全部直接在 route 函数里 `session.get(Item, id)` / `session.exec(select(...))`；`crud.py` 里只有 user 相关函数和 `create_item`。即官方模板对"薄 CRUD 域"的态度是：**route 即全部，不为对称性硬造一层**。
5. **无 service 层、无 repository 层**——整个 backend 没有任何 `service.py` / `repository.py`。

---

## 2. zhanymkanov/fastapi-best-practices（社区最高星实践指南）

来源：<https://github.com/zhanymkanov/fastapi-best-practices>（master README 的 *Project Structure* 章节，<https://github.com/zhanymkanov/fastapi-best-practices#project-structure>）。

README 给出的推荐结构（原文摘录）：

```
src
├── auth
│   ├── router.py
│   ├── schemas.py      # pydantic models
│   ├── models.py       # db models
│   ├── dependencies.py
│   ├── config.py       # local configs
│   ├── constants.py
│   ├── exceptions.py
│   ├── service.py
│   └── utils.py
├── aws
│   ├── client.py       # client model for external service communication
│   ├── schemas.py
│   ├── config.py
│   ├── constants.py
│   ├── exceptions.py
│   └── utils.py
├── posts
│   ├── router.py
│   ├── schemas.py
│   ├── models.py
│   ├── dependencies.py
│   ├── constants.py
│   ├── exceptions.py
│   ├── service.py
│   └── utils.py
├── config.py           # global configs
├── models.py           # global models
├── exceptions.py       # global exceptions
├── pagination.py       # global module e.g. pagination
├── database.py
└── main.py
```

### 关键事实

1. **每个业务域 = 一个包，最多 9 个文件**：`router.py`（"core of each module with all the endpoints"）、`schemas.py`、`models.py`、`service.py`（"module specific business logic"）、`dependencies.py`、`constants.py`、`config.py`、`utils.py`、`exceptions.py`。README 逐条列出各文件职责（原文编号列表 1–9）。
2. **文件是"按需存在"的，不是 9 个全建**：`aws` 这种纯外部服务域只有 6 个文件（client/schemas/config/constants/exceptions/utils），没有 `router.py`、`models.py`、`service.py`。
3. **没有 repository 层**。README 全文（845 行）grep 不到 "repository"；数据访问就是 `service.py` 直接写 SQLAlchemy——"SQL-first. Pydantic-second" 章节的示例代码注释即为 `# src.posts.service`（<https://github.com/zhanymkanov/fastapi-best-practices#sql-first-pydantic-second>）。
4. **按技术横切被明确标注为"小项目可用"**。README 原文："Many example projects and tutorials organize projects by file type (e.g., crud, routers, models), which works well for microservices or smaller projects. However, this approach didn't scale well for our monolith with many domains and modules."——并声明该竖切结构"inspired by Netflix's Dispatch, with some minor modifications"。
5. 跨域引用要求显式模块导入：`from src.auth import constants as auth_constants`、`from src.notifications import service as notification_service`。

---

## 3. FastAPI 官方文档 "Bigger Applications – Multiple Files"

来源：<https://fastapi.tiangolo.com/tutorial/bigger-applications/>。

官方教程给出的目录模式（原文）：

```
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── dependencies.py
│   └── routers
│       ├── __init__.py
│       ├── items.py
│       └── users.py
│   └── internal
│       ├── __init__.py
│       └── admin.py
```

### 关键事实

1. **推荐的是 `routers/` 按技术分层，一资源一文件**：`app/routers/items.py`、`app/routers/users.py`，加上共享的 `app/dependencies.py` 和 `app/main.py`。教程全篇没有出现按域分包（`app/items/`、`app/users/`）的示例。
2. **教程不规定 models/crud/service 的组织**——示例里 router 文件（如 `items.py`）包含该资源的全部 path operation 与逻辑，`fake_items_db` 就写在 router 文件里。
3. 官方立场是提供工具而非强加结构："**FastAPI** provides a convenience tool to structure your application while keeping all the flexibility."（即 `APIRouter`，被比作 Flask Blueprint）。
4. 唯一的"分组"维度示例是 `internal/`（内部管理端点）——按受众分组，而非按域分包。

---

## 4. Netflix/dispatch（大型生产单体的"上限"参照）

来源：<https://github.com/Netflix/dispatch>（main 分支，2026-08 当前状态）。`src/dispatch/` 下共 **47 个域包**（ai, auth, canvas, case, case_cost, case_cost_type, common, conference, conversation, cost_model, data, database, definition, document, email_templates, entity, entity_type, event, evergreen, feedback, forms, group, incident, incident_cost, incident_cost_type, incident_role, individual, messaging, monitor, notification, organization, participant, participant_activity, participant_role, plugin, plugins, project, report, route, search, search_filter, service, signal, static, storage, tag, tag_type, task, team, term, ticket, workflow——清单取自 `https://api.github.com/repos/Netflix/dispatch/contents/src/dispatch`）。

**最小 CRUD 域 `case_cost_type`（成本类型字典表）——4 个文件**（<https://github.com/Netflix/dispatch/tree/main/src/dispatch/case_cost_type>）：

```
src/dispatch/case_cost_type/
├── config.py    # 208 B
├── models.py    # DB 模型 + Create/Update schema（1.5 KB）
├── service.py   # get / get_by_name / get_all / create / update / delete（4.3 KB）
└── views.py     # APIRouter 端点（3.5 KB）
```

`service.py` 的真实内容（<https://github.com/Netflix/dispatch/blob/main/src/dispatch/case_cost_type/service.py>）就是**模块级函数直接 `db_session.query(CaseCostType)...`**，无类、无 repository：

```python
def get(*, db_session, case_cost_type_id: int) -> CaseCostType | None:
    return db_session.query(CaseCostType).filter(...).one_or_none()

def create(*, db_session, case_cost_type_in: CaseCostTypeCreate) -> CaseCostType:
    ...
    db_session.add(case_cost_type)
    db_session.commit()
    return case_cost_type
```

**复杂域 `case`——约 12 个条目，且域内再拆子包**（<https://github.com/Netflix/dispatch/tree/main/src/dispatch/case>）：

```
src/dispatch/case/
├── __init__.py
├── enums.py
├── flows.py             # 49.8 KB，工作流编排
├── messaging.py         # 20.5 KB
├── models.py            # 18 KB
├── priority/            # ← 子域长成嵌套包
├── scheduled.py
├── scheduled_internal.py
├── service.py           # 16 KB
├── severity/            # ← 子域嵌套包
├── type/                # ← 子域嵌套包
└── views.py             # 18 KB
```

### 关键事实

1. Netflix 规模的单体也是**按域竖切**，但域内文件清单是**按需生长的**：字典表域 4 文件（config/models/service/views），核心域才多出 enums/flows/messaging/scheduled 等专属文件。
2. 子概念（priority/severity/type）不是平铺进 `case/` 的文件堆，而是**升级为嵌套子包**——这是"域长大了再拆"的真实样本。
3. **全库无 repository 抽象**：数据访问统一为各域 `service.py` 的模块级函数，直接持有 `db_session`。

---

## 核心问题逐条回答

### a. 每个 domain/resource 实际几个文件？

- **官方模板（官方教程同款）**：每资源 **1 个** route 文件 + 全局共享的 `crud.py`/`models.py`。就"新增一个资源要动几个文件"而言：1 个 route 文件 + 在共享 `models.py`/`crud.py` 里追加。
- **zhanymkanov 指南**：业务域 **8–9 个**，但明确按需裁剪（无 DB 的 `aws` 域只有 6 个，无 service/models/router）。
- **Netflix Dispatch**：最小 CRUD 域 **4 个**（config/models/service/views），复杂域 10+。
- 结论：**"每域 6 个文件起步"没有一手依据；实践区间是 1（横切小项目）～ 4–9（竖切多域项目），且都是按需加文件。**

### b. CRUD-only 简单域是否要拆 repository/service？

**全部一手来源答案一致：不拆 repository；service 也不是必备。**

- 官方模板：`routes/items.py` 直接在端点函数里写 SQLModel 查询，`crud.py` 只为 user（有密码哈希、认证时序防护等真实逻辑）存在——**逻辑厚度决定是否抽层，而非对称性**。
- zhanymkanov：无 repository；`service.py` 承载数据访问 + 业务逻辑（SQLAlchemy 直写），只有纯外部客户端域反而用 `client.py` 替代。
- Dispatch：连 Netflix 的字典表域都只有函数式 `service.py`，无 repository 类。

即：**没有任何被调研的一手来源使用或推荐 repository 层**；它在 FastAPI 社区不是主流（这与 Java/Spring 传统不同）。service/crud 层出现的触发条件是"该域有可复用/可测试的业务逻辑，或被其他模块 import 复用"（Dispatch/zhanymkanov 的跨域 `from src.notifications import service` 模式），而不是"每个资源都要有"。

### c. 有没有"先单文件、长大了再拆包"的渐进式实践？

没有来源用这句话原文表述，但存在三段等价的、可组合的渐进证据：

1. **官方模板/官方文档就是"小项目形态"**：每资源 1 个文件，crud/models 全局平铺。zhanymkanov README 明确认可这种按文件类型组织 "works well for microservices or smaller projects"，只是"didn't scale well for our monolith"——即**规模（域数量）是切换结构的触发器**。
2. **竖切域内的文件是按需追加的**：aws 域没有 service/models/router；Dispatch 的域从 4 文件起步，出现 flows/messaging/scheduled 等职责时才加对应文件。
3. **域内子概念长大 → 拆嵌套子包**：Dispatch 的 `case/priority/`、`case/severity/`、`case/type/` 就是"文件长多了升级为包"的真实落地。

### d. 按域竖切 vs 按技术横切，主流是哪种？

**两种都算主流，分界线是项目规模（域数量）与团队约定，而非社区共识压倒一方：**

- **按技术横切**（`routers/`、`models.py`、`crud.py` 平铺）：FastAPI **官方文档**与**官方团队模板**采用；zhanymkanov 认可其适用于"microservices or smaller projects"。
- **按域竖切**（`src/<domain>/` 一域一包）：**社区最高星实践指南**（zhanymkanov，明确为多域单体推荐）与**Netflix Dispatch**（大型生产单体）采用；官方文档也不反对——它自陈只提供 `APIRouter` 工具并 "keeping all the flexibility"。

规律：**域少（约 <10 个）或微服务 → 横切足够；多域单体 → 竖切**。竖切阵营（zhanymkanov 原文）把结构灵感归于 Netflix Dispatch，两个来源互相印证。

---

## 证据支持的文件粒度建议

综合上述一手来源，可直接落地的粒度规则：

1. **路由永远一资源一文件**（所有 4 个来源一致）：横切时放 `api/routes/<resource>.py`；竖切时放 `<domain>/router.py`（Dispatch 叫 `views.py`）。
2. **schema 与 model 是"域内一个文件"，不是"每资源一组文件"**：横切 = 全局 `models.py`（官方模板）；竖切 = 域内 `schemas.py` + `models.py`（zhanymkanov/Dispatch）。没有任何来源把 `user_schemas.py`/`item_schemas.py` 拆成每资源一组。
3. **不为对称性建层**：
   - 薄 CRUD 域：逻辑写在 route 里即可（官方模板 `items.py`）。
   - 有复用价值的域：加一个 `service.py`（或 `crud.py`）承载函数式数据访问 + 业务逻辑。
   - **repository 层：无一手来源支持，默认不加。**
4. **竖切域的"标准三件套"是 router + models(+schemas) + service**（Dispatch 最小域 4 文件含 config）；`dependencies/constants/exceptions/config/utils` 按需出现，不预先创建。9 文件（zhanymkanov 上限）是成熟多域单体的形态，不是起点。
5. **拆包的触发器是"文件数/职责溢出"而非提前设计**：当一个域内某子概念需要自己的 model+service 时（Dispatch 的 `case/priority/`），或当项目域多到 `routers/` 平铺难以导航时（zhanymkanov 的单体经验），再做对应层级的拆分。
6. **规模分界**：约 10 个域以内、CRUD 为主的项目，官方模板的横切结构（每资源 1 route 文件 + 全局 models/crud）就是官方团队自己维护的"足够好"形态；多域单体再切换到 `src/<domain>/` 竖切。


---

## 5. 社区 skill 交叉验证（skills.sh，2026-08-30）

经 `npx skills find fastapi` 检索，按安装量取前 5 并直接读取源仓库全文：

| skill | installs | 布局要点 | service/repository | models 位置 |
|---|---|---|---|---|
| [fastapi/fastapi@fastapi](https://github.com/fastapi/fastapi/blob/HEAD/fastapi/.agents/skills/fastapi/SKILL.md)（官方，101.9K stars） | 8.6K | **不规定项目布局**，只给代码约定：`Annotated`+依赖类型别名、router 级 prefix/tags/deps、一函数一 HTTP 操作、禁 ellipsis/RootModel、`fastapi` CLI + `[tool.fastapi] entrypoint` | 无立场 | — |
| [wshobson/agents@fastapi-templates](https://github.com/wshobson/agents/blob/main/plugins/api-scaffolding/skills/fastapi-templates/SKILL.md) | 23.5K | `api/v1/endpoints/*.py` + `api/v1/router.py` + `api/dependencies.py`；models/schemas/services/repositories 全局按类分文件夹 | 有 repository（全局） | 全局 `models/user.py` |
| [mindrally/skills@fastapi-python](https://github.com/mindrally/skills/blob/main/fastapi-python/SKILL.md) | 12.4K | 仅代码风格（RORO、函数式、显式导出、`routers/user_routes.py` 命名） | — | — |
| [jeffallan/claude-skills@fastapi-expert](https://github.com/Jeffallan/claude-skills/blob/main/skills/fastapi-expert/SKILL.md) | 5.2K | 平铺 `routers/` + 单个 `crud.py`（模块级函数）+ `app.security`；Annotated `DbDep` 别名 | crud 函数，无 repository | 平铺 |
| [affaan-m/ECC@fastapi-patterns](https://github.com/affaan-m/ECC/blob/main/skills/fastapi-patterns/SKILL.md) | 5K | factory+lifespan、`dependencies.py`（DbDep/CurrentUserDep 别名）、`routers/` + 全局 `models/`、`schemas/`、`services/`；lifespan `create_all` 仅限 dev、生产走 Alembic | 有 service，无 repository | 全局 `models/user.py` |

交叉验证结论：

1. **`api/v1/` 版本化 API 目录 + 中央 router**：wshobson 与本 skill 一致。
2. **全局 `app/models/`（一域一文件）**：wshobson、affaan-m 均如此 —— 印证把 models 移出域文件的决定。
3. **共享依赖集中文件**：wshobson（`api/dependencies.py`）、affaan-m（`app/dependencies.py`）、官方模板（`api/deps.py`）三家都有 —— 已采纳为 `app/api/dependencies.py` 契约。
4. **repository 仅 wshobson 一家使用**；官方 skill、官方模板、jeffallan、affaan-m 均无 —— 维持"默认无 repository"。
5. **官方 skill 不规定项目布局** —— 竖切+三档与官方无冲突；其代码级约定（Annotated 别名、一函数一 HTTP 操作、async/def 选择）与本 skill 兼容，其中阻塞调用 pitfall 与 `fastapi` CLI 已并入。

本轮对 skill 的落地改动：`app/api/dependencies.py` 进入布局与 Module Boundaries（端点只从该文件导入依赖别名，SKILL.md/module-template/health/routing/responses 示例同步切换）；新增 "Blocking calls inside `async def`" pitfall；uv.md 增加 `[tool.fastapi] entrypoint` 与 `uv run fastapi dev`。