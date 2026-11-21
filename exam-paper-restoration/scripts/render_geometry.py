#!/usr/bin/env python3
"""
几何原图矢量校验与渲染辅助工具 (Geometric Diagram Validator & Renderer)

功能：
1. 校验纯黑白 SVG 几何图规范性（XML 语法、白底背景、纯黑白配色、推荐宽度、文本坐标越界）。
2. 将 SVG 转换为高清 PNG（用于不支持 SVG 的 Word/微信等场景），支持单图与 --output-dir 批量导出。

用法示例:
    python3 scripts/render_geometry.py --check-only resources/orig_q10.svg resources/orig_q12.svg
    python3 scripts/render_geometry.py resources/orig_q10.svg out/q10.png --scale 2
    python3 scripts/render_geometry.py --output-dir out/ --scale 2 resources/orig_q10.svg resources/orig_q12.svg
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
MONOCHROME_KEYWORDS = {
    "none",
    "transparent",
    "currentcolor",
    "black",
    "white",
    "gray",
    "grey",
    "silver",
    "dimgray",
    "dimgrey",
    "darkgray",
    "darkgrey",
    "lightgray",
    "lightgrey",
    "gainsboro",
    "whitesmoke",
}
WHITE_KEYWORDS = {"white", "#fff", "#ffffff", "rgb(255,255,255)"}


def _parse_px(value: str | None) -> float | None:
    if not value:
        return None
    match = re.match(r"^\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*(?:px)?\s*$", value)
    return float(match.group(1)) if match else None


def _is_monochrome_color(raw: str | None) -> bool:
    if not raw:
        return True
    val = re.sub(r"\s+", "", raw.strip().lower())
    if not val or val in MONOCHROME_KEYWORDS or val.startswith("url("):
        return True
    hex_match = re.match(r"^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$", val)
    if hex_match:
        h = hex_match.group(1)
        if len(h) == 3:
            return h[0] == h[1] == h[2]
        r, g, b = h[0:2], h[2:4], h[4:6]
        return r == g == b
    rgb_match = re.match(r"^rgba?\((\d+),(\d+),(\d+)(?:,[0-9.]+)?\)$", val)
    if rgb_match:
        return rgb_match.group(1) == rgb_match.group(2) == rgb_match.group(3)
    return False


def _is_white_fill(raw: str | None) -> bool:
    if not raw:
        return False
    val = re.sub(r"\s+", "", raw.strip().lower())
    return val in WHITE_KEYWORDS


def _extract_style_colors(style: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        key = key.strip().lower()
        if key in {"stroke", "fill", "color"}:
            found.append((key, val.strip()))
    return found


def validate_svg(svg_content: str) -> tuple[float | None, float | None, list[str]]:
    """校验 SVG 语法与试卷印刷规范，返回 (width, height, warnings)。高度不设硬限制。"""
    try:
        root = ET.fromstring(svg_content)
    except ET.ParseError as exc:
        raise ValueError(f"SVG XML 语法错误: {exc}") from exc

    tag_name = root.tag.split("}")[-1].lower()
    if tag_name != "svg":
        raise ValueError(f"根节点不是 <svg>，而是 <{tag_name}>")

    width = _parse_px(root.attrib.get("width"))
    height = _parse_px(root.attrib.get("height"))
    vb_min_x = 0.0
    vb_min_y = 0.0
    vb_width: float | None = None
    vb_height: float | None = None

    if "viewBox" in root.attrib:
        parts = re.split(r"[\s,]+", root.attrib["viewBox"].strip())
        if len(parts) == 4:
            try:
                vb_min_x, vb_min_y, vb_width, vb_height = (float(p) for p in parts)
                width = width if width is not None else vb_width
                height = height if height is not None else vb_height
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

    # 检查纯白底背景（避免暗色模式/微信预览下黑线透明不可见）
    has_white_bg = False
    non_mono_colors: set[str] = set()
    oob_texts: list[str] = []

    bound_w = vb_width if vb_width is not None else width
    bound_h = vb_height if vb_height is not None else height

    for elem in root.iter():
        local_tag = elem.tag.split("}")[-1].lower()
        fill_attr = elem.attrib.get("fill")
        stroke_attr = elem.attrib.get("stroke")
        style_attr = elem.attrib.get("style", "")
        style_pairs = _extract_style_colors(style_attr)

        if local_tag == "rect" and not has_white_bg:
            effective_fill = fill_attr
            for k, v in style_pairs:
                if k == "fill":
                    effective_fill = v
            if _is_white_fill(effective_fill):
                rw = elem.attrib.get("width", "").strip()
                rh = elem.attrib.get("height", "").strip()
                if (rw == "100%" or (_parse_px(rw) or 0) >= (bound_w or 0) * 0.9) and (
                    rh == "100%" or (_parse_px(rh) or 0) >= (bound_h or 0) * 0.9
                ):
                    has_white_bg = True

        for color_val in (fill_attr, stroke_attr):
            if color_val and not _is_monochrome_color(color_val):
                non_mono_colors.add(color_val)
        for _k, color_val in style_pairs:
            if not _is_monochrome_color(color_val):
                non_mono_colors.add(color_val)

        if local_tag == "text" and bound_w is not None and bound_h is not None:
            tx = _parse_px(elem.attrib.get("x"))
            ty = _parse_px(elem.attrib.get("y"))
            if tx is not None and (tx < vb_min_x or tx > vb_min_x + bound_w):
                oob_texts.append((elem.text or "").strip() or f"x={tx:g}")
            elif ty is not None and (ty < vb_min_y or ty > vb_min_y + bound_h):
                oob_texts.append((elem.text or "").strip() or f"y={ty:g}")

    if not has_white_bg:
        warnings.append(
            "未检测到覆盖画布的纯白背景 <rect fill=\"#ffffff\" />，在暗色模式或微信中黑线可能不可见"
        )
    if non_mono_colors:
        sample = ", ".join(sorted(non_mono_colors)[:5])
        warnings.append(
            f"检测到非纯黑白/灰度配色 ({sample})，原题印刷配图建议仅使用纯黑线框与白底"
        )
    if oob_texts:
        sample = ", ".join(oob_texts[:5])
        warnings.append(f"检测到文本坐标超出画布 viewBox 边界 ({sample})，导出后可能被裁切")

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
        description="校验纯黑白 SVG 几何原图并按需转换为高清 PNG（支持单图、批量与仅校验模式）。"
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help=(
            "单图转换: <input.svg|-> <output.png>；"
            "仅校验 (--check-only) 或批量转换 (--output-dir): 一个或多个 <input.svg>。"
        ),
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="仅校验 SVG 语法与试卷印刷规范（不生成 PNG）。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="批量导出目录：将每个输入 SVG 按同名 .png 输出到此目录。",
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


def _read_svg(path_arg: str) -> str:
    if path_arg == "-":
        return sys.stdin.read()
    input_path = Path(path_arg)
    if not input_path.exists():
        raise FileNotFoundError(f"找不到输入文件: {input_path}")
    return input_path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.check_only:
        exit_code = 0
        for item in args.paths:
            try:
                content = _read_svg(item)
                width, height, warnings = validate_svg(content)
            except Exception as exc:  # noqa: BLE001
                print(f"[ERROR] {item}: {exc}", file=sys.stderr)
                exit_code = 1
                continue
            for warn in warnings:
                print(f"[WARN] {item}: {warn}", file=sys.stderr)
            size_info = f"{width:g}x{height:g}px" if width and height else "未声明尺寸"
            print(f"[OK] {item}: 校验通过 ({size_info}, {len(warnings)} 条告警)")
        return exit_code

    if args.output_dir is not None:
        exit_code = 0
        for item in args.paths:
            if item == "-":
                print("[ERROR] --output-dir 模式不支持从标准输入 '-' 读取", file=sys.stderr)
                return 1
            try:
                content = _read_svg(item)
                out_path = args.output_dir / f"{Path(item).stem}.png"
                rendered = render_svg_to_png(
                    content,
                    out_path,
                    scale_factor=args.scale,
                    backend=args.backend,
                )
                print(f"[OK] 成功生成高清图: {rendered}")
            except Exception as exc:  # noqa: BLE001
                print(f"[ERROR] {item}: {exc}", file=sys.stderr)
                exit_code = 1
        return exit_code

    if len(args.paths) != 2:
        parser.error("单图转换需提供 <input_svg> <output_png> 两个路径，或使用 --check-only / --output-dir")

    input_arg, output_arg = args.paths
    try:
        svg_content = _read_svg(input_arg)
        out_path = render_svg_to_png(
            svg_content,
            output_arg,
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
