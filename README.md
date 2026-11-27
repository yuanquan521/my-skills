# my-skills

可复用的 AI Agent Skill 规范与脚手架模板仓库。每个 Skill 目录以 `SKILL.md` 为入口，按需附带 `references/`、`examples/`、`scripts/`、`resources/` 或 `evals/`。

## Skill 目录

1. `fastapi-backend-skill/` — FastAPI + PostgreSQL + SQLAlchemy + uv 后端项目固定结构与规范。

2. `flask-backend-skill/` — Flask + PostgreSQL + Flask-SQLAlchemy + 独立 APScheduler 进程后端项目规范。

3. `exam-paper-restoration/` — 试卷原题还原与错题翻新规范（去手写批改痕迹、标准符号与几何配图重绘）。

4. `answer-me-with-html/` — 按需将回答、流程、架构对比或视频总结渲染为单页可视化 HTML 文档或讲解视频（克制触发，单文件夹统一输出至 `AI-Outputs/`，保留中文文件名并关闭自动更新）。

5. `watch/` — 解析在线视频 URL 或本地视频（字幕/语音转写 + 关键帧提取/Gemini 识片），并联动 `answer-me-with-html` 生成 HTML 总结文档。

6. `math-learn/` — 小学及小升初数学深度解析、错因诊断、举一反三变式训练与互动陪学，默认生成单文件离线 HTML 学习单并保存至 `/Users/chengwei/Downloads/`（联动 `answer-me-with-html`，亦支持纯文字输出）。
