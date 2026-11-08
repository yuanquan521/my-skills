# HTML Template Reference

Use this reference when rendering a summary page. The template is self-contained: inline CSS only, no external requests, light-theme friendly.

## Filename Rules

| Case | Filename |
| --- | --- |
| Single URL, usable title | `<kebab-title>.html` (e.g. `ai-agents-in-production.html`) |
| Single URL, no usable title | `<domain>.html` (e.g. `example-com.html`) |
| Multiple URLs | `<kebab-title>.html` per URL + `index.html` |
| Collision with existing file | append `-2`, `-3`, ... before `.html` |

Slug rules: lowercase, non-alphanumeric runs → single `-`, trim `-`, max 60 chars, strip punctuation. If the title is empty or slugs to nothing, use the domain with dots replaced by `-`.

## Escaping Rules (mandatory)

Every piece of text originating from the fetched page passes through HTML escaping before entering the template:

- `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`, `"` → `&quot;`, `'` → `&#39;`
- URLs in `href` must be validated: allow only `http://`, `https://`, and `mailto:` schemes; anything else (notably `javascript:`) is dropped or replaced with plain text.
- Quotes from the source go inside `<blockquote>` as escaped plain text — never as raw HTML.

When a generator script builds the file, do the escaping in code (e.g. Python `html.escape`), not by hand-editing.

## Page Skeleton

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escaped page title} · 摘要</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 48px 20px 64px;
    font: 16px/1.75 -apple-system, "PingFang SC", "Hiragino Sans GB",
          "Microsoft YaHei", "Segoe UI", sans-serif;
    color: #1f2328; background: #ffffff;
    max-width: 760px; margin-inline: auto;
  }
  header { border-bottom: 2px solid #d0d7de; padding-bottom: 16px; margin-bottom: 8px; }
  h1 { font-size: 26px; line-height: 1.4; margin: 0 0 8px; }
  .meta { font-size: 13px; color: #59636e; }
  .meta a { color: #0969da; text-decoration: none; }
  .tldr { background: #f6f8fa; border-left: 4px solid #0969da;
          padding: 12px 16px; border-radius: 0 6px 6px 0; margin: 16px 0 24px; }
  h2 { font-size: 19px; margin: 28px 0 10px; }
  li { margin: 6px 0; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px;
         font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 90%; }
  footer { margin-top: 40px; padding-top: 12px; border-top: 1px solid #d0d7de;
           font-size: 12px; color: #59636e; }
  .failed { background: #fff8c5; border: 1px solid #d4a72c; border-radius: 6px; padding: 12px 16px; }
</style>
</head>
<body>
<header>
  <h1>{escaped page title}</h1>
  <div class="meta">
    来源：<a href="{validated href}" rel="noreferrer noopener">{escaped domain or site name}</a>
    · 抓取日期：{YYYY-MM-DD} · 生成日期：{YYYY-MM-DD}
  </div>
</header>

<div class="tldr"><strong>TL;DR</strong> — {escaped 2–4 sentences}</div>

<h2>关键要点</h2>
<ul>
  <li>{key point, escaped}</li>
  <!-- 5–8 items -->
</ul>

<!-- optional sections for longer sources: 核心论点 / 数据与事实 / 背景 -->
<h2>{escaped optional section}</h2>
<p>{escaped content}</p>

<footer>
  本页面由 URL 摘要 skill 生成本地文件，内容基于抓取时的公开页面归纳，可能与原文后续更新不一致。
  原文链接：<a href="{validated href}" rel="noreferrer noopener">{escaped full URL}</a>
</footer>
</body>
</html>
```

## Index Page (multi-URL runs)

`index.html` uses the same skeleton with:

- `h1` = run label (e.g. `URL 摘要 · {YYYY-MM-DD}`)
- one `<li>` per URL: `<a href="{file}.html">{escaped title}</a> — {escaped one-line digest} · {状态}` where 状态 is `成功` or `获取失败`
- a count line: `共 N 个链接：成功 X · 失败 Y`

## Constraints

- Total file size target: under 100 KB; do not embed source images.
- `lang` is `zh-CN`; all page text (chrome labels and summary content) is Chinese.
- No `<script>` tags. No external `<link>`, `@import`, or `url(...)` references.
- Keep valid structure: one `<h1>`, sections under `<h2>`, closed list items.
