/**
 * screenshot.js — capture key pages for debugging.
 *
 * Usage:
 *   node screenshot.js
 *
 * Saves PNGs to screenshots/<timestamp>/ and prints the paths.
 * Requires the app to be running (make backend + make frontend).
 */

const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = "http://localhost:5173";
const OUT  = path.join(__dirname, "screenshots", new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19));

const PAGES = [
  { name: "social-timeline",  url: `${BASE}/social` },
  { name: "social-agents",    url: `${BASE}/social/agents` },
  { name: "social-create",    url: `${BASE}/social/create` },
  { name: "lab-population",   url: `${BASE}/lab` },
  { name: "lab-network",      url: `${BASE}/lab/network` },
  { name: "lab-news",         url: `${BASE}/lab/news` },
  { name: "lab-runs",         url: `${BASE}/lab/runs` },
  { name: "about",            url: `${BASE}/lab/about` },
];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await chromium.launch();
  const page    = await browser.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });

  for (const { name, url } of PAGES) {
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
      await page.waitForTimeout(4500); // wait for async data fetches + render
      const file = path.join(OUT, `${name}.png`);
      await page.screenshot({ path: file, fullPage: true });
      console.log(`✓ ${name} → ${file}`);
    } catch (err) {
      console.error(`✗ ${name}: ${err.message}`);
    }
  }

  await browser.close();
  console.log(`\nScreenshots saved to: ${OUT}`);
})();
