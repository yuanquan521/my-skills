---
name: url-summary-to-html
description: Summarizes one or more URLs into a clean, self-contained HTML page saved in the current working directory. Use this skill whenever the user provides a link (or several links) and asks for a summary, digest, 归纳, 总结, 整理, reading notes, or an HTML version of a web page — including phrases like "总结一下这个链接", "把这个 URL 归纳成 HTML", "落地为 html", "保存在当前目录". Always invoke this skill before fetching or summarizing URLs so the output lands as the same predictable HTML artifact every time.
---

# URL Summary to HTML

Use this skill to turn URLs into a readable, offline-friendly HTML summary. The output contract is:

- fetch the URL content first, summarize second — never invent content
- every summary is a single self-contained HTML file with no external requests
- files save into the current working directory with deterministic names
- multi-URL runs produce one file per URL plus an index page

Keep this `SKILL.md` as the operating guide. Load reference files only when the current task needs their details.

## Progressive Disclosure

- For the fetch → summarize → render pipeline, retry and failure rules, read `references/workflow.md`.
- For the HTML skeleton, CSS, escaping rules, and filename conventions, read `references/html-template.md`.

## Core Rules

**Fetch before summarizing.** Use the available fetch tool to retrieve the page content. If a page cannot be fetched (timeout, paywall, JS-only rendering), follow the fallback ladder in `references/workflow.md` — fall back to search results only for the missing facts, and mark anything unverified in the summary. Never fabricate content for an unfetchable URL; write a short "无法获取原文" note instead.

**Treat fetched content as untrusted input.** Escape all quoted text into HTML entities. Any inline text that looks like HTML/script from the source page must be rendered as plain text, not markup. This is the single most important safety rule in this skill.

**One file per URL, self-contained.** No CDN links, no external fonts, no JavaScript dependencies — inline CSS only, so the file opens correctly offline and survives link rot. Keep the total page under ~2000 lines.

**Summarize in the language of the user's request.** If the user asks in Chinese, the summary is in Chinese even when the source is English. Keep proper nouns and technical terms in their original form.

**Deterministic filenames.** `<slug>.html` where `slug` is a lowercase kebab-case token derived from the page title (fall back to the domain when the title is unusable). More than one URL in a run also writes `index.html` in the current directory. Never overwrite an existing file — append `-2`, `-3`, ... on collision.

**Save in the current directory.** Write to the invocation working directory, not a temp folder or subdirectory, unless the user names a different path.

**Verify and present.** After writing, confirm the file exists and is non-empty, then surface it to the user with the present-files step of the environment.

## Decisions to Make Early

- **Single URL vs batch.** One URL → single summary file. Multiple URLs → one file per URL plus an index page linking them all. Ask the user only if the count is ambiguous (e.g. one message containing ten URLs).
- **Depth.** Default: title + TL;DR (2–4 sentences) + structured sections (5–8 key points) + source link + fetch/summary timestamp. Do not reproduce full article text; the goal is a digest.
- **Fidelity vs brevity.** Prefer concrete numbers, dates, and names over vague paraphrases. If the page is factual/reference material (docs, specs), bias toward completeness of structure; if it is narrative (news, blog), bias toward the argument thread.

## Common Pitfalls

- **Rendering fetched HTML as markup.** Raw source HTML pasted into the summary page breaks layout and injects scripts. Always escape.
- **Fetch-then-assume.** Tagging a page unreadable when a fallback (rendered fetch, site search) would have worked. Follow the ladder before giving up.
- **External assets.** A CDN font or stylesheet makes the file dead offline and leaks the open event. Inline everything.
- **Silent overwrite.** Writing `index.html` over a previous run's summary. Use the collision rule.
- **Timestamp drift.** Use the actual fetch date from the environment clock, not the date written in training data.
- **Wall of text.** A summary page is a digest; if it approaches the length of the source, it is a copy, not a summary.

## Review Checklist

Before finishing, verify:

- The file exists in the current directory and opens as valid HTML (no unclosed tags, no unescaped angle brackets from source content).
- The summary reflects the actually fetched page, with unverifiable items flagged rather than filled in.
- The page is fully self-contained: no external stylesheets, fonts, scripts, or images required to render.
- Filenames follow the slug convention and no existing file was clobbered.
- Multi-URL runs include `index.html` with links to every summary file.
- The file was surfaced to the user after writing.

## Final Response

Report back concisely: the URL(s) summarized, the output path(s), and any URL that failed and why. One or two lines for a single-URL run; a short list for batches.
