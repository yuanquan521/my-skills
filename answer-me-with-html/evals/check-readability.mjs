#!/usr/bin/env node
// Run: node answer-me-with-html/evals/check-readability.mjs (requires ego-browser).
// Measures rendered pages, including theme overrides, mobile overflow and text scaling.
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const cli = fileURLToPath(new URL('../scripts/am.mjs', import.meta.url));
const work = mkdtempSync(join(tmpdir(), 'am-readability-'));
const env = { ...process.env, AM_HOME: join(work, 'state'), AM_NO_UPDATE_CHECK: '1' };
const cases = [];
const content = `
这是一份需要持续阅读的中文笔记。正文、时间线和表格都应该在正常缩放下清楚可读。

## A 章节与时间线
### 阅读要点
先理解结论，再检查证据。这里保留足够长的段落，验证宽屏上的阅读区域，也检查手机上的自动换行。

\`\`\`timeline v
00:00–02:00 | Introduction | 阅读章节内容，确认时间、标题与详细说明在默认字号下都能清楚辨认。
* 02:00–05:00 | Monitor a Performance Rollout | 查看运行日志和发布结果，再根据证据确认下一步操作。
05:00–08:00 | Review the Fix | 阅读代码变更，保留完整的推理过程和验证结果。
\`\`\`

## B 数据与代码
| 检查项目 | 说明 |
|---|---|
| 正文与组件 | 保持可读字号，允许自然换行。 |
| 长链接 | https://example.com/very-long-path-that-must-not-force-the-document-to-overflow-on-a-small-phone |

\`\`\`js
const readable = true;
\`\`\`

## C 操作建议
\`\`\`callout info 阅读建议
按章节阅读，并通过目录返回需要复习的内容。
\`\`\`
`;

function run(args, input) {
  const result = spawnSync(process.execPath, [cli, ...args], { env, input, encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stdout + result.stderr);
}

try {
  for (const template of ['doc', 'sheet']) {
    for (const theme of ['paper', 'blueprint', 'shadcn']) {
      const file = join(work, `${template}-${theme}.html`);
      run(['render', '-', '--no-open', '-o', file], `---\ntitle: 阅读排版检查\ntemplate: ${template}\ntheme: ${theme}\nstyle: off\n---\n${content}`);
      cases.push({ url: pathToFileURL(file).href, template, theme });
    }
  }
  run(['config', 'set', 'scale', '1.5']);
  const large = join(work, 'doc-large-left.html');
  run(['render', '-', '--no-open', '-o', large], `---\ntitle: 放大阅读检查\ntemplate: doc\noutline: left\nstyle: off\n---\n${content}`);
  cases.push({ url: pathToFileURL(large).href, template: 'doc', theme: 'paper', scale: 1.5 });

  const browserScript = `
const task = await taskSpace('HTML 阅读排版回归检查');
const page = task.page('p1');
const failures = [];
try {
  for (const item of ${JSON.stringify(cases)}) {
    await page.goto(item.url);
    for (const width of [1920, 1366, 768, 390, 320]) {
      await page.cdp('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
      for (const mode of ['light', 'dark']) {
        const m = await page.evaluate(({ template, mode }) => {
          document.documentElement.dataset.mode = mode;
          const main = document.querySelector(template === 'doc' ? '.am-doc-body' : 'main');
          const css = (s) => getComputedStyle(document.querySelector(s));
          const font = (s) => parseFloat(css(s).fontSize);
          const rect = main.getBoundingClientRect();
          const text = css('.am-tl-text');
          return {
            body: font('.am-md p'), detail: font('.am-tl-text'), table: font('.am-md td'),
            heading: font('.am-md h3'), title: font('.am-panel-head h2'), code: font('.am-code'),
            lineHeight: parseFloat(text.lineHeight) / parseFloat(text.fontSize),
            width: rect.width, overflow: document.documentElement.scrollWidth - innerWidth,
          };
        }, { template: item.template, mode });
        const scale = item.scale || 1;
        const checks = {
          '正文至少 18px': m.body >= 18 * scale - 0.1,
          '时间线说明至少 17px': m.detail >= 17 * scale - 0.1,
          '表格至少 16px': m.table >= 16 * scale - 0.1,
          '代码至少 16px': m.code >= 16 * scale - 0.1,
          '小标题大于正文': m.heading > m.body,
          '时间线行高至少 1.6': m.lineHeight >= 1.59,
          '页面无横向溢出': m.overflow <= 1,
          '长文充分使用屏幕宽度': item.template !== 'doc' || width < 1000 || m.width >= Math.min(width - 64, 1440) - 1,
        };
        const failed = Object.keys(checks).filter((key) => !checks[key]);
        if (failed.length) failures.push({ template: item.template, theme: item.theme, width, mode, scale, failed, measured: m });
      }
    }
  }
} finally {
  await page.cdp('Emulation.clearDeviceMetricsOverride');
  await task.finish({ keep: [] });
}
console.log(JSON.stringify({ checks: ${cases.length} * 5 * 2, failures }));
`;
  const browser = spawnSync('ego-browser', ['nodejs', '-e', browserScript], { encoding: 'utf8', maxBuffer: 4 * 1024 * 1024 });
  if (browser.status !== 0) throw new Error(browser.stdout + browser.stderr);
  const output = browser.stdout + browser.stderr;
  const line = output.split('\n').find((line) => line.startsWith('{"checks":'));
  if (!line) throw new Error('Missing browser check result: ' + output);
  const result = JSON.parse(line);
  if (result.failures.length) {
    console.error(JSON.stringify(result.failures.slice(0, 3), null, 2));
    console.error(`FAIL: ${result.failures.length}/${result.checks} page/viewport/mode combinations`);
    process.exitCode = 1;
  } else {
    console.log(`PASS: ${result.checks} page/viewport/mode combinations`);
  }
} finally {
  rmSync(work, { recursive: true, force: true });
}
