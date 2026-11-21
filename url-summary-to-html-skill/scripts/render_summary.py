#!/usr/bin/env python3
"""
URL 摘要 HTML 确定性渲染器 (Deterministic Self-Contained HTML Summary Renderer)

接收结构化 JSON，自动完成 HTML 实体转义、URL Scheme 白名单校验、
防覆盖文件命名（含中文标题友好 Slug）、单页与多页 index.html 生成及输出自检。

用法示例:
    python3 scripts/render_summary.py summary.json --output-dir .
    cat summary.json | python3 scripts/render_summary.py - --output-dir .
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https", "mailto"}
MAX_SLUG_ASCII = 60
MAX_SLUG_UNICODE = 40
MAX_FILE_BYTES = 100 * 1024

BASE_CSS = """\
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
  blockquote { margin: 12px 0; padding: 8px 14px; border-left: 3px solid #d0d7de;
               color: #59636e; background: #f6f8fa; border-radius: 0 4px 4px 0; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px;
         font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 90%; }
  footer { margin-top: 40px; padding-top: 12px; border-top: 1px solid #d0d7de;
           font-size: 12px; color: #59636e; word-break: break-all; }
  .failed { background: #fff8c5; border: 1px solid #d4a72c; border-radius: 6px; padding: 12px 16px; margin-top: 20px; }
  .note { background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px; padding: 12px 16px; margin-top: 20px; }
  .badge-ok { color: #1a7f37; font-weight: 600; }
  .badge-fail { color: #cf222e; font-weight: 600; }"""


def esc(value: Any) -> str:
    """严格 HTML 转义（包含双引号与单引号）。"""
    return html.escape(str(value or ""), quote=True)


def validate_href(url: str | None) -> str | None:
    """仅允许 http / https / mailto 协议，拦截 javascript:/data: 等危险 URI。"""
    if not url:
        return None
    raw = url.strip()
    parsed = urlparse(raw)
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        return None
    if scheme in {"http", "https"} and not parsed.netloc:
        return None
    return raw


def render_link(url: str | None, label: str) -> str:
    """安全渲染链接；非法协议降级为纯文本。"""
    safe_url = validate_href(url)
    escaped_label = esc(label)
    if not safe_url:
        return f"<code>{escaped_label}</code>"
    return f'<a href="{esc(safe_url)}" rel="noreferrer noopener">{escaped_label}</a>'


def sanitize_ascii_slug(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned[:MAX_SLUG_ASCII].strip("-")


def sanitize_unicode_slug(text: str) -> str:
    # 保留中英文字符、数字与连字符，剔除文件系统危险字符与标点
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip().lower())
    cleaned = cleaned.replace("_", "-")
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned[:MAX_SLUG_UNICODE].strip("-")


def domain_fallback_slug(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "url-summary").lower()
    if host.startswith("www."):
        host = host[4:]
    host_slug = sanitize_ascii_slug(host) or "url-summary"
    path_segments = [seg for seg in parsed.path.split("/") if seg]
    if path_segments:
        tail = sanitize_ascii_slug(path_segments[-1])
        if tail and tail not in {"index", "html", "htm", "php", "aspx"}:
            return f"{host_slug}-{tail}"[:MAX_SLUG_ASCII].strip("-")
    return host_slug


def make_slug(item: dict[str, Any]) -> str:
    explicit = str(item.get("slug") or "").strip()
    if explicit:
        slug = sanitize_ascii_slug(explicit) or sanitize_unicode_slug(explicit)
        if slug:
            return slug

    title = str(item.get("title") or "").strip()
    if title and title != "无法获取原文":
        ascii_slug = sanitize_ascii_slug(title)
        # 若标题主要是英文（ASCII 有效字符足够且不含过多汉字），优先使用英文 kebab-slug
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", title))
        if len(ascii_slug) >= 4 and cjk_count == 0:
            return ascii_slug
        # 中文/混合标题优先保留可读 Unicode slug，避免全部退化为 domain-2.html
        unicode_slug = sanitize_unicode_slug(title)
        if len(unicode_slug) >= 2:
            return unicode_slug

    return domain_fallback_slug(str(item.get("final_url") or item.get("url") or ""))


def resolve_unique_path(output_dir: Path, stem: str, reserved: set[Path]) -> Path:
    """确定性防覆盖路径：若已存在或被本批占用，依次追加 -2, -3, ..."""
    candidate = output_dir / f"{stem}.html"
    counter = 2
    while candidate.exists() or candidate in reserved:
        candidate = output_dir / f"{stem}-{counter}.html"
        counter += 1
    reserved.add(candidate)
    return candidate


def render_page_html(item: dict[str, Any], default_date: str) -> str:
    orig_url = str(item.get("url") or "").strip()
    final_url = str(item.get("final_url") or orig_url).strip()
    status = str(item.get("status") or "ok").strip().lower()
    fetch_date = str(item.get("fetch_date") or default_date).strip()
    published_date = str(item.get("published_date") or "").strip()

    parsed = urlparse(final_url or orig_url)
    site_name = str(item.get("site_name") or parsed.netloc or orig_url or "未知来源").strip()
    title = str(item.get("title") or "").strip() or (
        "无法获取原文" if status == "failed" else site_name
    )

    meta_parts = [f"来源：{render_link(final_url or orig_url, site_name)}"]
    if published_date:
        meta_parts.append(f"发布日期：{esc(published_date)}")
    meta_parts.append(f"抓取日期：{esc(fetch_date)}")
    meta_html = " · ".join(meta_parts)

    body_chunks: list[str] = []
    if status == "failed":
        attempted = item.get("attempted_steps") or []
        attempted_text = "；".join(str(s).strip() for s in attempted if str(s).strip())
        if not attempted_text:
            attempted_text = "抓取原文"
        reason = str(
            item.get("reason") or "页面需要登录、付费墙、反爬限制或链接已失效。"
        ).strip()
        body_chunks.append(
            '<section class="failed">\n'
            "  <h2>无法获取原文</h2>\n"
            f"  <p>目标 URL：<code>{esc(orig_url)}</code></p>\n"
            f"  <p>已尝试：{esc(attempted_text)}。</p>\n"
            f"  <p>可能原因：{esc(reason)}</p>\n"
            "</section>"
        )
    else:
        tldr = str(item.get("tldr") or "").strip()
        if tldr:
            body_chunks.append(
                f'<div class="tldr"><strong>TL;DR</strong> — {esc(tldr)}</div>'
            )

        key_points = [str(p).strip() for p in (item.get("key_points") or []) if str(p).strip()]
        if key_points:
            lis = "\n".join(f"  <li>{esc(p)}</li>" for p in key_points)
            body_chunks.append(f"<h2>关键要点</h2>\n<ul>\n{lis}\n</ul>")

        for sec in item.get("sections") or []:
            if not isinstance(sec, dict):
                continue
            heading = str(sec.get("heading") or "").strip()
            paragraphs = [str(p).strip() for p in (sec.get("paragraphs") or []) if str(p).strip()]
            bullets = [str(b).strip() for b in (sec.get("bullets") or []) if str(b).strip()]
            quotes = [str(q).strip() for q in (sec.get("quotes") or []) if str(q).strip()]
            if not (heading or paragraphs or bullets or quotes):
                continue
            sec_lines: list[str] = []
            if heading:
                sec_lines.append(f"<h2>{esc(heading)}</h2>")
            for para in paragraphs:
                sec_lines.append(f"<p>{esc(para)}</p>")
            if bullets:
                sec_lines.append("<ul>")
                sec_lines.extend(f"  <li>{esc(b)}</li>" for b in bullets)
                sec_lines.append("</ul>")
            for quote in quotes:
                sec_lines.append(f"<blockquote>{esc(quote)}</blockquote>")
            body_chunks.append("\n".join(sec_lines))

        uncertainty = str(item.get("uncertainty") or "").strip()
        if uncertainty:
            body_chunks.append(
                '<section class="note">\n'
                "  <h2>争议与不确定项</h2>\n"
                f"  <p>{esc(uncertainty)}</p>\n"
                "</section>"
            )

    footer_link = render_link(orig_url or final_url, orig_url or final_url)
    body_html = "\n\n".join(body_chunks)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)} · 摘要</title>\n"
        f"<style>\n{BASE_CSS}\n</style>\n"
        "</head>\n"
        "<body>\n"
        "<header>\n"
        f"  <h1>{esc(title)}</h1>\n"
        f'  <div class="meta">{meta_html}</div>\n'
        "</header>\n\n"
        f"{body_html}\n\n"
        "<footer>\n"
        "  本页面由 URL 摘要 skill 生成本地文件，内容基于抓取时的公开页面归纳，可能与原文后续更新不一致。\n"
        f"  原文链接：{footer_link}\n"
        "</footer>\n"
        "</body>\n"
        "</html>\n"
    )


def render_index_html(
    entries: list[dict[str, Any]],
    index_title: str,
    run_date: str,
) -> str:
    ok_count = sum(1 for e in entries if e["status"] != "failed")
    fail_count = len(entries) - ok_count

    li_lines: list[str] = []
    for entry in entries:
        is_failed = entry["status"] == "failed"
        badge = (
            '<span class="badge-fail">获取失败</span>'
            if is_failed
            else '<span class="badge-ok">成功</span>'
        )
        digest = entry["digest"] or ("无法获取原文" if is_failed else "")
        digest_part = f" — {esc(digest)}" if digest else ""
        li_lines.append(
            f'  <li><a href="{esc(entry["filename"])}">{esc(entry["title"])}</a>'
            f'{digest_part} · {esc(entry["fetch_date"])} · {badge}</li>'
        )

    title_text = f"{index_title} · {run_date}"
    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title_text)}</title>\n"
        f"<style>\n{BASE_CSS}\n</style>\n"
        "</head>\n"
        "<body>\n"
        "<header>\n"
        f"  <h1>{esc(title_text)}</h1>\n"
        f'  <div class="meta">共 {len(entries)} 个链接：成功 {ok_count} · 失败 {fail_count} · 生成日期：{esc(run_date)}</div>\n'
        "</header>\n\n"
        "<h2>摘要目录</h2>\n"
        "<ul>\n"
        f"{chr(10).join(li_lines)}\n"
        "</ul>\n\n"
        "<footer>\n"
        "  本索引页由 URL 摘要 skill 生成，所有条目均指向同目录离线 HTML 文件。\n"
        "</footer>\n"
        "</body>\n"
        "</html>\n"
    )


def verify_rendered_html(path: Path, content: str) -> list[str]:
    warnings: list[str] = []
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"生成的 HTML 文件为空: {path}")
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        warnings.append(f"{path.name} 体积超过 100KB 建议上限")
    if re.search(r"<script\b", content, re.IGNORECASE):
        raise RuntimeError(f"安全校验失败：输出包含 <script> 标签 ({path.name})")
    if re.search(r"<link\b[^>]*href=", content, re.IGNORECASE):
        raise RuntimeError(f"自包含校验失败：输出包含外部 <link> 引用 ({path.name})")
    if re.search(r"url\(\s*['\"]?https?://", content, re.IGNORECASE):
        raise RuntimeError(f"自包含校验失败：CSS 包含外部 url() 引用 ({path.name})")
    return warnings


def render_bundle(payload: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        if "url" in payload:
            raw_items = [payload]
        else:
            raise ValueError("输入 JSON 必须包含非空的 items 列表或单条 url 对象")

    output_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    reserved: set[Path] = set()
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []

    for item in raw_items:
        if not isinstance(item, dict) or not item.get("url"):
            raise ValueError("每个条目都必须包含 url 字段")
        stem = make_slug(item)
        out_path = resolve_unique_path(output_dir, stem, reserved)
        page_html = render_page_html(item, default_date=today)
        out_path.write_text(page_html, encoding="utf-8")
        warnings.extend(verify_rendered_html(out_path, page_html))

        status = str(item.get("status") or "ok").strip().lower()
        tldr = str(item.get("tldr") or "").strip()
        digest = str(item.get("digest") or (tldr[:80] + ("…" if len(tldr) > 80 else ""))).strip()
        entries.append(
            {
                "url": str(item["url"]),
                "title": str(item.get("title") or ("无法获取原文" if status == "failed" else stem)),
                "status": status,
                "filename": out_path.name,
                "path": str(out_path.resolve()),
                "fetch_date": str(item.get("fetch_date") or today),
                "digest": digest,
            }
        )

    index_path: Path | None = None
    if len(entries) > 1:
        index_title = str(payload.get("index_title") or "URL 摘要").strip()
        index_path = resolve_unique_path(output_dir, "index", reserved)
        index_html = render_index_html(entries, index_title=index_title, run_date=today)
        index_path.write_text(index_html, encoding="utf-8")
        warnings.extend(verify_rendered_html(index_path, index_html))

    return {
        "files": entries,
        "index_path": str(index_path.resolve()) if index_path else None,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将结构化 URL 摘要 JSON 渲染为安全、自包含的本地 HTML 文件。"
    )
    parser.add_argument(
        "input_json",
        help="输入 JSON 文件路径；传 '-' 表示从标准输入读取。",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="输出目录（默认当前工作目录 '.'）。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    raw_text = (
        sys.stdin.read()
        if args.input_json == "-"
        else Path(args.input_json).read_text(encoding="utf-8")
    )
    payload = json.loads(raw_text)
    out_dir = Path(payload.get("output_dir") or args.output_dir)
    result = render_bundle(payload, out_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
