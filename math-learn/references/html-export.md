# 离线单文件 HTML 学习单落地规范

查阅时机：**默认在完成单题完整解析或多题批量解析后立即读取并执行本规范**（仅在互动陪学问答阶段或用户明确要求纯文字回复时跳过）。

---

## 1. 路径、命名与符号规则

- **默认保存目录**：一律保存至 **`/Users/chengwei/Downloads/`**（即 `~/Downloads/`），无论采用 `answer-me-with-html` 还是备用自包含 HTML 方案均遵守该默认目录；仅当用户明确指定了其他保存路径时，改写入用户指定路径。
- **文件名规范**：
  - 单题：`小学数学-<核心模型或主题>解析.html`（例如 `/Users/chengwei/Downloads/小学数学-火车过桥行程问题解析.html`）。
  - 多题：`小学数学-错题解析汇总-<日期或主题>.html`（例如 `/Users/chengwei/Downloads/小学数学-错题解析汇总-20261127.html`）。
  - 若目标路径下已存在同名文件，在扩展名前追加 `-2` 或时间戳（如 `-20261127-1605`），避免覆盖已有学习单。
- **离线自包含**：所有样式、图表、SVG 和原题图片全部内嵌在单个 `.html` 文件中，无外部 CDN 依赖，断网可直接打开与打印。
- **符号与 `$` 转义防坑**：延续 [SKILL.md](../SKILL.md) 第 1 节纯文本数学符号规范，禁用 LaTeX 源码。**特别注意**：`answer-me-with-html` 会把成对 `$` 解析为数学公式界定符，若题干涉及美元金额（如 `$5`），在草稿中统一写作“5 美元”或转义为 `\$5`，避免触发公式误解析。

---

## 2. 优先方案：联动 `answer-me-with-html` 渲染

按以下顺序探测 `am.mjs`（找到即优先使用，避免手写整页 CSS）：

1. `<math-learn-dir>/../answer-me-with-html/scripts/am.mjs`
2. `~/.gemini/config/skills/answer-me-with-html/scripts/am.mjs`、`~/.agents/skills/answer-me-with-html/scripts/am.mjs`、`~/.claude/skills/answer-me-with-html/scripts/am.mjs`、`~/.codex/skills/answer-me-with-html/scripts/am.mjs`
3. 全局命令 `am`

### 推荐 Frontmatter
```yaml
---
template: doc
theme: paper
lang: zh
style: off
title: 小学数学解析：<题型与核心主题>
subtitle: <所属专题> · <关键技巧> · 举一反三训练
source: <题号或来源>
---
```

> 使用 `template: doc` + `theme: paper` + `style: off`：自带侧边目录大纲与纸质阅读质感，且不因短句检查截断完整推导与变式题。

### 推荐章节与组件搭配（按题型选配）

| 章节 | 推荐组件 | 作用 |
|---|---|---|
| A 原题与核心结论 | 原题图片 `![说明](/abs/path.png)` + `kv cols=2`（多题模式加「题号与答案速查表」） | 保留原图证据，一屏看清条件、题眼与答案 |
| B 直观图解 | 数值对比/盈亏/变化趋势用 `chart bar`（支持负数）/ `chart line` / `chart pie`；**几何图形、辅助线割补、线段图、行程路线图**用简洁内联 `svg` 块 | 把抽象数量关系或空间割补画清楚，不硬套统计图 |
| C 详细解析与验算 | 有序步骤 + Markdown 验算表（状态列用 `ok` / `no`） | 先直观法再进阶/巧算法，末尾表格闭环验算 |
| D 错因、知识点与陷阱 | 若含孩子错解先列「孩子错因诊断」+ Markdown 知识点表 + `callout err` | 精准指出个人错因，红框警示头号陷阱 |
| E 万能解题模板 | `flow LR` + 家长启发提问列表 | 沉淀 3–5 步通用流程与陪学话术 |
| F 举一反三 | 阶梯变式总览表 + 变式 1–3 逐题解析 + 变式 4 挑战题与升级思路点拨及答案 | 基础 → 反转 → 经典母题 → 高阶拓展 |

### 执行命令（显式 `-o` 输出至 `/Users/chengwei/Downloads/`）

```bash
node "<answer-me-with-html-dir>/scripts/am.mjs" render - -o "/Users/chengwei/Downloads/小学数学-<核心模型或主题>解析.html" <<'AM_EOF'
...草稿内容...
AM_EOF
```

- 确认输出行以 `✓` 开头且路径位于 `/Users/chengwei/Downloads/`（或用户指定路径）；本地原题截图直接填绝对路径，`am.mjs` 会自动内联进单文件 HTML。
- 若渲染报 `✗ L<line>` 并给出 `draft: <path>`，用文件编辑工具修正该草稿的报错行后重跑：
  ```bash
  node "<answer-me-with-html-dir>/scripts/am.mjs" render "<draft-path>" -o "/Users/chengwei/Downloads/小学数学-<核心模型或主题>解析.html"
  ```

---

## 3. 备用方案：无 `am` CLI 或需纯净打印版时的自包含 HTML

当环境没有 `answer-me-with-html`，或用户明确要求**纯净可打印的 A4 纸质错题学习单（含空白题区与分页答案区）**时，直接生成单个 `.html` 文件并写入 `/Users/chengwei/Downloads/小学数学-<核心模型或主题>解析.html`（或用户指定路径）：

1. **视觉风格**：暖白纸面阅读感（背景 `#FAF9F6`，卡片 `#FFFFFF`，正文 `#1F2937`，强调色深蓝 `#1D4ED8`，易错警示框浅红底 `#FEF2F2` + 左侧红条 `#DC2626`），内容区最大宽度 `860px` 居中，字体优先系统中文无衬线体，关键算式用淡灰底 `<code>` 标签突出显示。
2. **原题图片内嵌**：若有本地原题图片，转为 Base64 Data URI 写入 `<img src="data:image/...;base64,...">`，保证单文件转发仍可正常显示。
3. **直观图解**：用简洁内联 SVG 或 CSS 比例条展示几何辅助线、线段图或份数盈亏对比，不引入外部图表库。
4. **A4 打印友好**：内置 `@page { size: A4; margin: 16mm; }` 与 `@media print` 规则（隐藏装饰阴影、保留边框、关键模块加 `break-inside: avoid` 防跨页截断）；若用户需要“先做后对答案”的打印版，把解析或变式答案区设 `break-before: page`。

---

## 4. 预览与交付

- **预览方式**：
  - 使用 `answer-me-with-html` 时，遵循 `am` 自身配置；仅当 `am` 未自动打开且需要预览时，再用系统默认浏览器打开（macOS 执行 `open "<绝对路径>"`），避免重复打开双标签页。
  - 使用备用方案且需要预览时，使用系统默认浏览器打开（macOS 执行 `open "<绝对路径>"`），严禁使用 Agent 内置浏览器。
- **最终回复**：在对话中简洁给出**最终答案、核心题眼/错因一句话结论**以及可点击 `file://` 文件链接，不把整段 HTML 源码贴在对话里。
