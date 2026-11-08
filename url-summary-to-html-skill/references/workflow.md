# Workflow Reference

Use this reference when running the fetch → summarize → render pipeline, especially for pages that fail to fetch or contain little extractable text.

## Pipeline

1. **Normalize input.** Deduplicate URLs, drop tracking query params where harmless (`utm_*`, `spm`), and record the original URL verbatim in the summary footer regardless.
2. **Fetch.** Use the environment's web-fetch tool per URL. Record for each URL: final URL (after redirects), page title, publish date (if present), author/site, and main content as markdown.
3. **Assess content quality.** Call the fetch a failure if any of these hold: HTTP error, empty content, content shorter than ~200 chars that is mostly navigation/chrome, a paywall or login wall, or language clearly unrelated to the page (a wrong-page redirect).
4. **Fallback ladder.** Attempt in order; stop at the first success:
   1. Re-fetch the redirect-resolved URL.
   2. Fetch with a browser-style tool (rendered page) when available, for JS-heavy sites.
   3. Search for the page title + domain to recover a cached/alternate summary of the same content.
   4. Declare the URL unreadable and write a placeholder summary stating what was tried. Never fabricate the missing content.
5. **Summarize.** Produce, in Chinese:
   - one-line title (from the page, not the URL)
   - TL;DR of 2–4 sentences
   - 5–8 structured key points with concrete facts (numbers, dates, names, claims)
   - a "争议/不确定" (uncertainty) note whenever the source is speculative, any fallback step was used, or a fact could not be verified directly; identify which claims came from an alternate source
6. **Render.** Build the HTML per `references/html-template.md`, escaping all source-derived text and generated summaries, including titles, TL;DRs, and index digests.
7. **Write and verify.** Save to the current directory per the filename rules, re-read the file head/tail to confirm it is complete, then present it.

## Failure Note Template

When a URL fails after the full ladder, its file still renders, with the body replaced by:

```html
<section class="failed">
  <h2>无法获取原文</h2>
  <p>目标 URL：<code>{escaped_url}</code></p>
  <p>已尝试：{escaped list of steps actually performed}.</p>
  <p>可能原因：页面需要登录、付费墙、反爬限制或链接已失效。</p>
</section>
```

List only steps that actually ran. If browser rendering or search was unavailable, omit it from "已尝试" and optionally record that it was not run because the tool was unavailable. Never claim an unexecuted fallback was attempted.

And its index entry is marked `获取失败`.

## Multi-URL Rules

- One summary file per URL — never merge articles into one body; the index page provides the join.
- `index.html` lists every URL in run order: title, one-line digest, link to its file, fetch date, and failure status.
- Cap a single run at ~10 URLs. Beyond that, ask the user to batch the request.

## Timestamps

Get the real date from the environment clock at render time (e.g. a `date` command), format as `YYYY-MM-DD`, and stamp it in the page header and footer. Do not hardcode or recall dates.
