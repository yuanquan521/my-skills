# my-skills

可复用的 AI Agent Skill 规范与脚手架模板仓库。每个 Skill 目录以 `SKILL.md` 为入口，按需附带 `references/`、`examples/`、`scripts/`、`resources/` 或 `evals/`。

## Skill 目录

1. `fastapi-backend-skill/` — FastAPI + PostgreSQL + SQLAlchemy + uv 后端项目固定结构与规范。

2. `flask-backend-skill/` — Flask + PostgreSQL + Flask-SQLAlchemy + 独立 APScheduler 进程后端项目规范。

3. `exam-paper-restoration/` — 试卷原题还原与错题翻新规范（去手写批改痕迹、标准符号与几何配图重绘）。

4. `answer-me-with-html/` — 将复杂问答、流程、架构与对比转化为单页可视化 HTML 文档或讲解视频。

5. `watch/` — 解析在线视频 URL 或本地视频（字幕/语音转写 + 关键帧提取/Gemini 识片）。
