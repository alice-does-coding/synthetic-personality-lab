import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const svgPath = resolve(__dirname, '../frontend/public/favicon.svg');
const svg = readFileSync(svgPath, 'utf8');

const variants = [
  {
    out: resolve(__dirname, '../frontend/public/og-image.png'),
    width: 1200, height: 630,
    logoPx: 280, titlePx: 52, tagPx: 22, logoMb: 36,
  },
  {
    out: resolve(__dirname, '../frontend/public/og-image-square.png'),
    width: 1200, height: 1200,
    logoPx: 520, titlePx: 64, tagPx: 26, logoMb: 56,
  },
];

const makeHtml = (v) => `<!doctype html>
<html><head><meta charset="utf-8"><style>
  html, body { margin: 0; padding: 0; background: #0b0d12; }
  body {
    width: ${v.width}px; height: ${v.height}px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
    color: #f5f5f7;
  }
  .logo { width: ${v.logoPx}px; height: ${v.logoPx}px; margin-bottom: ${v.logoMb}px; }
  .title { font-size: ${v.titlePx}px; font-weight: 600; letter-spacing: -0.01em; }
  .tag { margin-top: 14px; font-size: ${v.tagPx}px; color: #9aa0aa; font-weight: 400; }
</style></head>
<body>
  <div class="logo">${svg}</div>
  <div class="title">Synthetic Personality Lab</div>
  <div class="tag">Measuring personality drift in LLM agents</div>
</body></html>`;

const browser = await chromium.launch();
for (const v of variants) {
  const page = await browser.newPage({ viewport: { width: v.width, height: v.height }, deviceScaleFactor: 2 });
  await page.setContent(makeHtml(v));
  await page.screenshot({ path: v.out, type: 'png', omitBackground: false });
  await page.close();
  console.log('wrote', v.out);
}
await browser.close();
