---
name: url-summary-to-html-skill
description: >-
  Summarizes one or more URLs into clean, self-contained Chinese HTML files saved in
  the current working directory (with an index page for multi-URL batches). Use
  whenever the user provides one or more links and asks to save, export, archive, or
  turn them into an HTML summary / offline reading note — including phrases like
  "把这个 URL 归纳成 HTML", "落地为 html", "做成离线阅读页", "总结链接并保存 HTML",
  "保存到当前目录", or batch-archiving multiple links. Do not trigger when the user
  only wants a quick inline chat explanation of a URL without creating any file.
---

# URL Summary to HTML

Turn one or more URLs into readable, offline-friendly Chinese HTML summary files saved in the current working directory.

## Output Contract

- Fetch the URL content first, summarize second — never fabricate content for an unfetchable page.
- Render every file through `<skill-dir>/scripts/render_summary.py` so HTML escaping, URL scheme validation, collision-safe filenames, and multi-URL `index.html` generation happen deterministically in code.
- Produce one self-contained HTML file per URL (inline CSS only, zero external requests, no `<script>`) saved in the current working directory unless the user specifies another directory.

Keep this `SKILL.md` as the operating guide. Load reference files only when needed:

- Fetch → assess → fallback ladder → failure note → multi-URL rules: read [references/workflow.md](references/workflow.md).
- JSON schema for `scripts/render_summary.py`, HTML template, Chinese/English slug rules, and escaping guarantees: read [references/html-template.md](references/html-template.md).

## Core Rules

1. **Fetch before summarizing.** Retrieve each URL with the available web-fetch tool. If a page fails (HTTP error, empty/short chrome-only text, JS-only shell, paywall/login wall), follow the fallback ladder in [references/workflow.md](references/workflow.md) — never bypass CAPTCHAs or login walls, and never invent missing content. Unfetchable URLs render as a `status: "failed"` note listing only the fallback steps actually executed.
2. **Treat fetched content as untrusted input.** Always render through `<skill-dir>/scripts/render_summary.py` (which applies `html.escape(..., quote=True)` to every text field and allows only `http://`, `https://`, and `mailto:` in `href`). Never hand-paste raw fetched HTML into the output file.
3. **One self-contained file per URL.** Inline CSS only, no CDN fonts/stylesheets, no `<script>` tags, no embedded source images. Keep each file under 100 KB / ~2000 lines.
4. **Summarize in Chinese.** All chrome labels and summary prose are Chinese regardless of the source page's language; keep proper nouns, code identifiers, and technical terms in their original form.
5. **Readable, collision-safe filenames.** Prefer a concise English kebab-case `slug` (for English titles, or a short English translation for Chinese titles), or let `render_summary.py` preserve a readable Chinese/Unicode slug rather than collapsing every Chinese link to `domain-2.html`. Never overwrite an existing file (`-2`, `-3`, ... on collision, including `index.html`).
6. **Save in the current working directory.** Write to `.` unless the user specifies another directory; never hide deliverables in `/tmp`.
7. **Verify and report.** Confirm the output path(s) returned by `render_summary.py` exist and are non-empty. If your environment provides a file-presentation tool, surface the files; otherwise provide direct clickable paths in your reply.

## Decisions to Make Early

- **Single URL vs batch.** 1 URL → single HTML file; 2–10 URLs → one HTML file per URL plus `index.html`. Above ~10 URLs, ask the user how to batch.
- **Depth.** Default: title + TL;DR (2–4 sentences) + 5–8 concrete key points + optional structured sections + source link + real fetch date. Produce a digest, not a full-text mirror.
- **Fidelity vs brevity.** Favor concrete numbers, dates, versions, and names over vague paraphrases. Reference docs/specs bias toward structural completeness; news/essays bias toward argument flow.

## Common Pitfalls

- **Hand-editing HTML instead of running `render_summary.py`.** Risks unescaped `<script>`/`<` injection or broken tags.
- **Chinese titles collapsing to `mp-weixin-qq-com-2.html`.** Provide an explicit concise `slug` or rely on `render_summary.py`'s Unicode slug support.
- **Claiming unexecuted fallbacks.** In a failure note, list only the fallback steps that actually ran.
- **Hardcoding dates from training data.** Leave `fetch_date` omitted (or read from the system clock) so `render_summary.py` stamps the real date.
- **Triggering file writes unasked.** If a user only asks "what is this link about?" in chat without mentioning HTML/file output, answer in chat instead of writing `.html` files into their workspace.

## Review Checklist

- [ ] Rendered via `<skill-dir>/scripts/render_summary.py` (HTML escaped, `href` scheme validated, no `<script>` or external assets).
- [ ] Summary matches actually fetched content; fallbacks or unverified claims are noted in `uncertainty`, and unreadable URLs use `status: "failed"`.
- [ ] Saved in the current working directory (or user-specified path) with readable, non-colliding filenames; multi-URL batches include `index.html`.
- [ ] Final response concisely lists summarized URL(s), output file path(s), and any failed URLs with reasons.
