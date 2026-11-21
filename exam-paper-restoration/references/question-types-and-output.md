# 题型排版、配图边界与交付格式参考

本文件提供各常见题型的还原模板、配图重绘边界判断规则，以及可打印 A4 HTML 交付规范。

---

## 一、常见题型还原模板

### 1. 填空题
- 括号填空统一清空为全角空格：`（　　　　）`。
- 下划线填空保留长度适中的下划线：`________`。
- 括号内若原卷印有单位（如 `（　　　）厘米` 或 `（　　　cm）`），原样保留。

### 2. 选择题
- 清除题干括号里的手写字母、选项前的勾选/涂圈/划掉线。
- 严格保留原选项编号风格（`A.` / `A、` / `(A)`）和选项顺序；短选项可同行排布，长选项分行排布：

```markdown
**2.** 下列图形中，对称轴条数最多的是（　　）。
A. 等边三角形　　B. 正方形　　C. 等腰梯形　　D. 圆
```

### 3. 判断题
- 清空手写 `√`、`×` 及老师批改符号，题末统一还原为 `（　）`。

### 4. 计算题与方程题
- 保留题目要求（如“直接写出得数”“脱式计算，能简算的要简算”“解方程”）、原小问编号（`(1)`、`①` 等）。
- 上下分式用 `\frac{a}{b}`，方程组用 `\begin{cases}...\end{cases}`；竖式计算若原卷以横式给出，保持横式并留空等号后结果。

### 5. 表格题
- 使用标准 Markdown 表格完整还原表头、行头及原卷印刷已知数据，清空手写填写格：

```markdown
| 商品名称 | 单价（元） | 数量（件） | 总价（元） |
| :--- | :---: | :---: | :---: |
| 笔记本 | 6.5 | 4 | |
| 钢笔 | 18 | | 54 |
```

### 6. 解答题 / 复合应用题
- 完整保留情境背景、各小问编号与分值标注（如 `（6分）`）。
- 仅在用户需要打印空白重测卷时，在题下方预留空白作答区（HTML 打印模式自动留白，纯 Markdown 无需堆叠大量空行）。

---

## 二、配图重绘边界与文件约定

### 何时用矢量 SVG 重绘 vs 保留原图

| 图形类型 | 推荐处理方式 |
| :--- | :--- |
| 平面几何（三角形、梯形、圆、组合图形） | **SVG 矢量重绘**：严格按题设数值计算坐标，纯黑线框白底，不加辅助线 |
| 数轴、简易坐标系、线段图、示意图 | **SVG 矢量重绘**：保留原卷刻度、箭头与已知标注 |
| 简单统计图（条形图、折线图、扇形图） | **SVG 矢量重绘**：忠实还原坐标轴刻度、图例与已知数值 |
| 复杂实物照片、写实插画、地图、生物/地理彩图 | **不强行重绘**：标注 `[原卷此处含实物/写实配图，建议裁剪原图贴入]`，避免重绘失真 |

### 配图尺寸与导出约定
- **尺寸**：宽度推荐 `280px ～ 400px`（约占正文宽度 40% ～ 55%），**高度由图形真实几何比例与图注自然决定，不设死高度上限**；四周留白约 10% ～ 15%。
- **格式选择**：
  - Markdown 预览 / HTML 打印：优先直接引用 `.svg`（无损清晰、体积小），并可用 `--check-only` 先做质量校验（检查白底、纯黑白、宽度与文本越界）。
  - 需导入 Word、微信或不支持 SVG 的编辑器：用 [render_geometry.py](../scripts/render_geometry.py) 转为 2x 高清 `.png`（命令中的 `<skill-dir>` 替换为本技能目录路径）：
    ```bash
    # 仅校验 SVG 规范性
    python3 <skill-dir>/scripts/render_geometry.py --check-only q10.svg q12.svg
    # 单图转高清 PNG
    python3 <skill-dir>/scripts/render_geometry.py q10.svg q10.png --scale 2
    # 多图批量转高清 PNG
    python3 <skill-dir>/scripts/render_geometry.py --output-dir out/ --scale 2 q10.svg q12.svg
    ```
- **文件命名与路径**：多题落盘时优先放于输出文档同级的 `assets/`（或用户指定目录），按原题号命名（如 `q10.svg`、`q12.svg`），若重名追加 `-2`、`-3` 防覆盖。

---

## 三、可打印 A4 错题卷 HTML 模板（按需使用）

当用户要求“导出可打印的错题卷 / A4 练习纸 / 生成 HTML”时，产出**单个自包含 HTML 文件**（内联 CSS 与内联 SVG，无外部 CDN/字体依赖，打开即可 `Cmd+P` / `Ctrl+P` 打印）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{试卷/错题卷标题}</title>
<style>
  @page { size: A4; margin: 18mm 16mm; }
  * { box-sizing: border-box; }
  body {
    margin: 0 auto; max-width: 780px; padding: 28px 24px;
    font: 15px/1.85 "Songti SC", "SimSun", "Noto Serif CJK SC", serif;
    color: #111; background: #fff;
  }
  header { text-align: center; border-bottom: 1.5px solid #222; padding-bottom: 10px; margin-bottom: 20px; }
  h1 { font-size: 20px; margin: 0 0 6px; letter-spacing: 1px; }
  .meta { font-size: 13px; color: #555; }
  .question { margin-bottom: 22px; break-inside: avoid; page-break-inside: avoid; }
  .figure { margin: 10px 0 8px; text-align: center; }
  .figure svg, .figure img { max-width: 380px; height: auto; }
  .answer-space { height: 90px; } /* 仅解答题按需添加 */
  /* 纯 CSS 上下分式：<span class="frac"><span class="num">3</span><span class="den">4</span></span> */
  .frac { display: inline-flex; flex-direction: column; align-items: center; vertical-align: middle; line-height: 1.1; margin: 0 2px; font-size: 0.9em; }
  .frac .num { border-bottom: 1px solid #111; padding: 0 3px 1px; }
  .frac .den { padding: 1px 3px 0; }
  /* 表格题印刷边框 */
  table { border-collapse: collapse; margin: 10px 0; width: auto; min-width: 60%; font-size: 14px; }
  th, td { border: 1px solid #222; padding: 6px 12px; text-align: center; }
  th { background: #f5f5f5; font-weight: 600; }
  .check-list {
    margin-top: 28px; padding: 12px 16px; border: 1px dashed #999;
    font-size: 13px; color: #444; background: #fafafa;
  }
  .answers { margin-top: 32px; padding-top: 16px; border-top: 1.5px solid #222; break-before: page; }
  @media print {
    body { padding: 0; max-width: none; }
    .no-print { display: none; }
  }
</style>
</head>
<body>
<header>
  <h1>{试卷/错题卷标题}</h1>
  <div class="meta">姓名：________　日期：________　得分：________</div>
</header>

<section class="question">
  <p><strong>10.</strong> 如图，<em>AB</em> = 10 分米，<em>CD</em> = 4 分米，∠<em>A</em> = 45°，∠<em>B</em> 和 ∠<em>D</em> 都是直角。那么四边形 <em>ABCD</em> 的面积是（　　　　）平方分米。</p>
  <div class="figure"><!-- 内联纯黑白 SVG --></div>
</section>

<!-- 若有存疑项，加 .no-print 可在打印时自动隐藏或由用户决定 -->
<!-- 若用户需要参考答案，放入 <section class="answers">（打印时自动另起一页） -->
</body>
</html>
```

注意事项：
- HTML 中数学变量斜体用 `<em>A</em>`，上下分式可用纯 CSS inline-flex 分式样式（无需依赖外链 KaTeX CDN），确保离线打开与打印 100% 可用。
- `.question` 设置 `break-inside: avoid`，避免打印时题干与配图被分页拆成两半；参考答案（如有）放在 `.answers` 并设置 `break-before: page`，方便家长单独留存答案页。
