# Workflow Reference

Use this reference when running the fetch → summarize → render pipeline, especially for pages that fail to fetch or contain little extractable text.

## Pipeline

1. **Normalize input.** Deduplicate URLs, drop harmless tracking query params (`utm_*`, `spm`) when fetching, and preserve the user's original URL verbatim in `url` for the summary footer.
2. **Fetch.** Use the environment's web-fetch tool per URL. Record: `final_url` (after redirects), page title, publish date (if present), author/site name, and main content.
3. **Assess content quality.** Treat the fetch as failed if any of these hold: HTTP error, empty content, content shorter than ~200 chars that is mostly navigation/chrome, a paywall/login wall/CAPTCHA gate, or an obvious wrong-page redirect.
4. **Fallback ladder.** Attempt in order; stop at the first success:
   1. Re-fetch the redirect-resolved URL (if redirected).
   2. Fetch with a browser/rendered-page tool when available, for JS-heavy public pages. **Never attempt to solve or bypass a CAPTCHA, anti-bot challenge, login wall, or paywall** — if blocked, stop and move to step 3 or 4.
   3. Search for the page title + domain to recover a public alternate summary or official mirror; clearly mark which claims came from search/alternate sources in `uncertainty`.
   4. Declare the URL unreadable (`status: "failed"`) and record only the steps actually executed in `attempted_steps`. Never fabricate missing content.
5. **Summarize (in Chinese).** Prepare a JSON item per URL containing:
   - `title`: concise Chinese or original-plus-Chinese page title (not the raw URL)
   - `slug`: concise English kebab-case slug (recommended for Chinese titles so filenames stay portable and readable)
   - `tldr`: 2–4 sentences capturing the core conclusion
   - `key_points`: 5–8 concrete points with numbers, dates, names, and verifiable claims
   - `sections`: optional structured subsections (`heading`, `paragraphs`, `bullets`, `quotes`) for longer articles
   - `uncertainty`: note whenever the source is speculative, a fallback search was used, or facts could not be directly verified
6. **Render via script.** Pipe the JSON payload into `<skill-dir>/scripts/render_summary.py` (`--output-dir .` or the user-specified directory). Do not hand-assemble raw HTML when the script is available.
7. **Verify and report.** Inspect the JSON output from `render_summary.py`, confirm non-empty output files and zero security warnings, and report the summarized URLs, output paths, and any failed URLs concisely.

## Multi-URL Rules

- One summary file per URL — never merge distinct articles into a single body; `render_summary.py` automatically generates `index.html` whenever `len(items) > 1`.
- `index.html` also follows the collision rule (`index-2.html`, ...) so running a second batch never clobbers a previous index.
- Cap a single run at ~10 URLs; beyond that, ask the user how to split the batch.

## Timestamps

Leave `fetch_date` omitted (or read from the environment clock via `date +%Y-%m-%d`) so `render_summary.py` stamps the real date automatically. Never hardcode dates from training data.
