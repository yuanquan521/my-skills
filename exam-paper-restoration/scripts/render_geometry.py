#!/usr/bin/env python3
"""
几何原图矢量渲染辅助工具 (Geometric Diagram Helper)

将纯黑白 SVG 几何线框图转换为高清 PNG（用于不支持 SVG 的 Word/微信等场景）。
Markdown 与 HTML 交付优先直接使用 .svg，仅在需要位图时调用本脚本。

用法示例:
    python3 scripts/render_geometry.py resources/orig_q10.svg out/q10.png --scale 2
    cat diagram.svg | python3 scripts/render_geometry.py - out/q10.png --scale 2

后端自动降级顺序 (--backend auto):
    1. rsvg-convert (librsvg)
    2. resvg
    3. cairosvg (Python 包)
    4. qlmanage (macOS 内置快速预览渲染)
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

RECOMMENDED_MIN_WIDTH = 160.0
RECOMMENDED_MAX_WIDTH = 600.0


def _parse_px(value: str | None) -> float | None:
    if not value:
        return None
    match = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(?:px)?\s*$", value)
    return float(match.group(1)) if match else None


def validate_svg(svg_content: str) -> tuple[float | None, float | None, list[str]]:
    """校验 SVG 语法合法性，并返回 (width, height, warnings)。高度不设硬限制。"""
    try:
        root = ET.fromstring(svg_content)
    except ET.ParseError as exc:
        raise ValueError(f"SVG XML 语法错误: {exc}") from exc

    tag_name = root.tag.split("}")[-1].lower()
    if tag_name != "svg":
        raise ValueError(f"根节点不是 <svg>，而是 <{tag_name}>")

    width = _parse_px(root.attrib.get("width"))
    height = _parse_px(root.attrib.get("height"))

    if (width is None or height is None) and "viewBox" in root.attrib:
        parts = re.split(r"[\s,]+", root.attrib["viewBox"].strip())
        if len(parts) == 4:
            try:
                width = width if width is not None else float(parts[2])
                height = height if height is not None else float(parts[3])
            except ValueError:
                pass

    warnings: list[str] = []
    if width is not None:
        if width < RECOMMENDED_MIN_WIDTH:
            warnings.append(
                f"SVG 宽度偏小 ({width:g}px < {RECOMMENDED_MIN_WIDTH:g}px)，顶点字母可能不易辨认"
            )
        elif width > RECOMMENDED_MAX_WIDTH:
            warnings.append(
                f"SVG 宽度偏大 ({width:g}px > {RECOMMENDED_MAX_WIDTH:g}px)，建议控制在 280px~400px 左右"
            )
    return width, height, warnings


def _find_rsvg_convert() -> str | None:
    return shutil.which("rsvg-convert") or (
        "/opt/homebrew/bin/rsvg-convert"
        if os.path.exists("/opt/homebrew/bin/rsvg-convert")
        else None
    )


def _render_with_rsvg(svg_path: Path, out_path: Path, scale: float) -> None:
    rsvg_bin = _find_rsvg_convert()
    if not rsvg_bin:
        raise RuntimeError("未找到 rsvg-convert（macOS 可执行 `brew install librsvg` 安装）")
    cmd = [rsvg_bin, "-z", f"{scale:g}", str(svg_path), "-o", str(out_path)]
    subprocess.run(cmd, check=True)


def _render_with_resvg(svg_path: Path, out_path: Path, scale: float) -> None:
    resvg_bin = shutil.which("resvg")
    if not resvg_bin:
        raise RuntimeError("未找到 resvg（可执行 `brew install resvg` 安装）")
    cmd = [resvg_bin, "--zoom", f"{scale:g}", str(svg_path), str(out_path)]
    subprocess.run(cmd, check=True)


def _render_with_cairosvg(svg_content: str, out_path: Path, scale: float) -> None:
    try:
        import cairosvg  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("未安装 cairosvg（可执行 `uv pip install cairosvg` 安装）") from exc
    cairosvg.svg2png(bytestring=svg_content.encode("utf-8"), write_to=str(out_path), scale=scale)


def _render_with_qlmanage(
    svg_path: Path, out_path: Path, width: float | None, height: float | None, scale: float
) -> None:
    ql_bin = shutil.which("qlmanage")
    if not ql_bin:
        raise RuntimeError("当前系统无 qlmanage（仅 macOS 可用）")
    max_side = int(max(width or 360.0, height or 260.0) * scale)
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [ql_bin, "-t", "-s", str(max_side), "-o", tmpdir, str(svg_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        generated = Path(tmpdir) / f"{svg_path.name}.png"
        if not generated.exists():
            raise RuntimeError("qlmanage 未能生成 PNG 输出")
        shutil.move(str(generated), str(out_path))


def render_svg_to_png(
    svg_content: str,
    output_png_path: str | Path,
    scale_factor: float = 2.0,
    backend: str = "auto",
) -> Path:
    """将 SVG 字符串渲染为高清 PNG 图片并返回输出路径。"""
    if scale_factor <= 0:
        raise ValueError("scale_factor 必须大于 0")

    width, height, warnings = validate_svg(svg_content)
    for warn in warnings:
        print(f"[WARN] {warn}", file=sys.stderr)

    out_path = Path(output_png_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_svg = Path(tmpdir) / "diagram.svg"
        temp_svg.write_text(svg_content, encoding="utf-8")

        if backend == "rsvg-convert":
            _render_with_rsvg(temp_svg, out_path, scale_factor)
            return out_path
        if backend == "resvg":
            _render_with_resvg(temp_svg, out_path, scale_factor)
            return out_path
        if backend == "cairosvg":
            _render_with_cairosvg(svg_content, out_path, scale_factor)
            return out_path
        if backend == "qlmanage":
            _render_with_qlmanage(temp_svg, out_path, width, height, scale_factor)
            return out_path
        if backend != "auto":
            raise ValueError(f"不支持的渲染后端: {backend}")

        attempts = (
            ("rsvg-convert", lambda: _render_with_rsvg(temp_svg, out_path, scale_factor)),
            ("resvg", lambda: _render_with_resvg(temp_svg, out_path, scale_factor)),
            ("cairosvg", lambda: _render_with_cairosvg(svg_content, out_path, scale_factor)),
            (
                "qlmanage",
                lambda: _render_with_qlmanage(temp_svg, out_path, width, height, scale_factor),
            ),
        )
        errors: list[str] = []
        for name, runner in attempts:
            try:
                runner()
                return out_path
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{name}: {exc}")

        joined = "\n  - ".join(errors)
        raise RuntimeError(
            "所有 PNG 渲染后端均不可用，建议直接交付 .svg 文件，或安装 librsvg (`brew install librsvg`):\n"
            f"  - {joined}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将纯黑白 SVG 几何原图转换为高清 PNG（自动降级选择可用渲染器）。"
    )
    parser.add_argument(
        "input_svg",
        help="输入 SVG 文件路径；传 '-' 表示从标准输入读取 SVG 内容。",
    )
    parser.add_argument(
        "output_png",
        help="输出 PNG 文件路径。",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=2.0,
        help="缩放倍率（默认 2.0，双倍视网膜高清分辨率）。",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "rsvg-convert", "resvg", "cairosvg", "qlmanage"),
        default="auto",
        help="指定渲染后端（默认 auto 按 rsvg-convert -> resvg -> cairosvg -> qlmanage 降级）。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.input_svg == "-":
        svg_content = sys.stdin.read()
    else:
        input_path = Path(args.input_svg)
        if not input_path.exists():
            print(f"[ERROR] 找不到输入文件: {input_path}", file=sys.stderr)
            return 1
        svg_content = input_path.read_text(encoding="utf-8")

    try:
        out_path = render_svg_to_png(
            svg_content,
            args.output_png,
            scale_factor=args.scale,
            backend=args.backend,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] 成功生成高清图: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
