# HTML Template & Renderer Reference

Use `<skill-dir>/scripts/render_summary.py` to generate every summary page and multi-URL `index.html`. Doing escaping, URL scheme validation, and collision avoidance in Python code prevents accidental XSS, broken markup, and silent file overwrites.

## Running the Bundled Renderer

Pass structured JSON via stdin or a temporary JSON file:

```bash
cat <<'EOF' | python3 <skill-dir>/scripts/render_summary.py - --output-dir .
{
  "index_title": "URL 摘要",
  "items": [
    {
      "url": "https://example.com/posts/agent-evals",
      "final_url": "https://example.com/posts/agent-evals",
      "site_name": "Example Engineering",
      "title": "AI Agent 评测实践指南",
      "slug": "ai-agent-evals-guide",
      "published_date": "2026-10-15",
      "status": "ok",
      "tldr": "本文系统总结了生产环境 AI Agent 的评测指标与回归流程...",
      "key_points": [
        "区分离线单元测试与端到端轨迹评测，优先自动化客观断言。",
        "每次提示词或工具变更至少对比基线运行 3 次以观察方差。"
      ],
      "sections": [
        {
          "heading": "核心方法论",
          "paragraphs": ["作者将评测分为触发准确率、任务完成率与成本延迟三个维度。"],
          "quotes": ["原文关键引述（自动转义为纯文本，不解析 HTML）"]
        }
      ],
      "uncertainty": ""
    }
  ]
}
EOF
```

Failed fetch item shape:

```json
{
  "url": "https://example.com/paywalled-article",
  "title": "无法获取原文",
  "status": "failed",
  "attempted_steps": ["直接抓取（HTTP 403）", "站点标题检索（无公开全文）"],
  "reason": "目标站点存在付费墙或登录限制。"
}
```

`render_summary.py` prints a JSON report containing every generated file's resolved path, `index_path` (when `len(items) > 1`), and any size warnings.

## Filename & Slug Rules

| Case | Filename |
| --- | --- |
| Explicit `slug` field (recommended for Chinese titles) | `<kebab-slug>.html` (e.g. `ai-agent-evals-guide.html`) |
| English title (no explicit `slug`) | `<kebab-title>.html` (lowercase ASCII, max 60 chars) |
| Chinese / mixed title (no explicit `slug`) | Readable sanitized Unicode slug (max 40 chars, e.g. `ai-agent-评测实践指南.html`) |
| Unusable / empty title | `<domain>-<path-tail>.html` or `<domain>.html` |
| Multiple URLs | One `<slug>.html` per URL + `index.html` |
| Collision with existing file (including `index.html`) | Append `-2`, `-3`, ... before `.html` |

> **Why this matters for Chinese pages:** Stripping non-ASCII characters blindly turns every WeChat / Zhihu / Chinese blog title into an empty string, causing batch runs to produce opaque `mp-weixin-qq-com.html`, `mp-weixin-qq-com-2.html` files. Prefer supplying a concise English `slug`, or let `render_summary.py` keep a readable Chinese slug.

## Security & Escaping Guarantees

Enforced automatically by `scripts/render_summary.py`:

- All source-derived and generated text passes through `html.escape(..., quote=True)` (`&`, `<`, `>`, `"`, `'`).
- `href` attributes accept only `http://`, `https://`, and `mailto:` schemes; anything else (notably `javascript:`, `data:`) degrades to escaped plain text.
- Source quotes render inside `<blockquote>` as escaped plain text — never raw HTML.
- Post-write verification fails if `<script>`, external `<link href=...>`, or CSS `url(http...)` appears, and warns if file size exceeds 100 KB.

## Header Metadata & Layout

- `lang="zh-CN"`, light-theme inline CSS, responsive `max-width: 760px`, system CJK font stack.
- Header `.meta` shows: `来源：<site> · 发布日期：<YYYY-MM-DD>（若有） · 抓取日期：<YYYY-MM-DD>` (avoiding redundant "抓取日期 + 生成日期").
- `fetch_date` defaults automatically to the system clock (`datetime.date.today().isoformat()`) when omitted.
- Multi-URL `index.html` displays the run count (`共 N 个链接：成功 X · 失败 Y`) and links every local file with its digest, fetch date, and `成功` / `获取失败` status badge.
