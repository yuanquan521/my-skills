# my-skills

可复用的 AI Agent Skill 规范与脚手架模板仓库。每个 Skill 目录以 `SKILL.md` 为入口，按需附带 `references/`、`examples/`、`scripts/`、`resources/` 或 `evals/`。

## Skill 目录

- `fastapi-backend-skill/`（`fastapi-backend-structure`）— FastAPI + PostgreSQL + SQLAlchemy + uv 后端项目固定结构与规范。
- `flask-backend-skill/`（`flask-backend-skill`）— Flask + PostgreSQL + Flask-SQLAlchemy + 独立 APScheduler 进程后端项目规范。
- `url-summary-to-html-skill/`（`url-summary-to-html`）— 归纳总结提供的 URL，产出自包含 HTML 并保存在当前目录。
- `exam-paper-restoration/`（`exam-paper-restoration`）— 试卷原题还原与错题翻新规范（去手写批改痕迹、标准符号与几何配图重绘）。

更多仓库级约定与各 Skill 参考索引见 [AGENTS.md](AGENTS.md)。
