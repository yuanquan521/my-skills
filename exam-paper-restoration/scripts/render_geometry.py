#!/usr/bin/env python3
"""
几何原图矢量渲染辅助脚本 (Geometric Diagram Helper)
功能：将标准 SVG 几何线框图通过 rsvg-convert 转换为超清、免失真的 PNG 印刷图。

【配图尺寸与比例约束规范】：
1. 几何比例保真：图形长短比例与角度必须严格按题设数值绘制（如 45° 必须严格为等腰直角三角开度，3:1 比例线段长短必须明显成比例）。
2. 画幅尺寸适中：
   - 宽度：280px ~ 360px
   - 高度：180px ~ 250px
   - 画布留白 (Padding)：10% ~ 15%，防止字母标签贴边或裁切。
   - 杜绝生成全屏巨图或不可辨认的过小微缩图。
"""

import os
import subprocess
import sys

def render_svg_to_png(svg_content: str, output_png_path: str, scale_factor: int = 2):
    """
    将 SVG 字符串渲染为高清 PNG 图片。
    scale_factor: 2 表示双倍视网膜超清分辨率 (Retina)
    """
    temp_svg = output_png_path + ".tmp.svg"
    try:
        with open(temp_svg, "w", encoding="utf-8") as f:
            f.write(svg_content)
        
        # 优先使用 rsvg-convert (macOS Homebrew 常见路径)
        rsvg_bin = "/opt/homebrew/bin/rsvg-convert"
        if not os.path.exists(rsvg_bin):
            rsvg_bin = "rsvg-convert"
            
        cmd = [rsvg_bin, "-z", str(scale_factor), temp_svg, "-o", output_png_path]
        subprocess.run(cmd, check=True)
        print(f"[OK] 成功生成高清图: {output_png_path}")
    finally:
        if os.path.exists(temp_svg):
            os.remove(temp_svg)

if __name__ == "__main__":
    # 示例：绘制标准直角四边形 (原卷第10题样式)
    demo_svg = """<svg viewBox="0 0 320 260" width="320" height="260" xmlns="http://www.w3.org/2000/svg">
      <rect width="100%" height="100%" fill="#ffffff" />
      <polygon points="50,180 250,180 250,93.1 193.4,36.5" fill="#ffffff" stroke="#000000" stroke-width="2" />
      <polyline points="236,180 236,166 250,166" fill="none" stroke="#000000" stroke-width="1.5" />
      <polyline points="184.9,45 193.4,53.5 201.9,45" fill="none" stroke="#000000" stroke-width="1.5" />
      <path d="M 90,180 A 40 40 0 0 0 78.3,151.7" fill="none" stroke="#000000" stroke-width="1.5" />
      <text x="92" y="168" font-family="'Times New Roman', serif" font-size="16" fill="#000000">45°</text>
      <text x="25" y="190" font-family="'Times New Roman', serif" font-style="italic" font-size="20" fill="#000000">A</text>
      <text x="258" y="190" font-family="'Times New Roman', serif" font-style="italic" font-size="20" fill="#000000">B</text>
      <text x="258" y="98" font-family="'Times New Roman', serif" font-style="italic" font-size="20" fill="#000000">C</text>
      <text x="187" y="24" font-family="'Times New Roman', serif" font-style="italic" font-size="20" fill="#000000">D</text>
      <text x="150" y="235" font-family="'Songti SC', serif" font-size="16" fill="#000000" text-anchor="middle">（第 10 题）</text>
    </svg>"""
    
    out_dir = os.path.dirname(os.path.abspath(__file__))
    target_png = os.path.join(out_dir, "../resources/demo_q10.png")
    os.makedirs(os.path.dirname(target_png), exist_ok=True)
    render_svg_to_png(demo_svg, target_png)
