/**
 * report.js — health check + screenshot report.
 *
 * Polls the backend until it's ready (no blind sleep),
 * captures screenshots of all pages, checks key API endpoints,
 * and writes a markdown report to reports/<timestamp>.md
 *
 * Usage: node report.js
 * Requires services to already be starting (called from make report).
 */

const { chromium } = require("playwright");
const http  = require("http");
const https = require("https");
const fs    = require("fs");
const path  = require("path");

const API_BASE  = "http://127.0.0.1:8080/api";
const FRONT_BASE = "http://localhost:5173";
const TIMESTAMP  = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
const REPORT_DIR = path.join(__dirname, "reports");
const SHOT_DIR   = path.join(REPORT_DIR, TIMESTAMP, "screenshots");
const REPORT_FILE = path.join(REPORT_DIR, `${TIMESTAMP}.md`);

const PAGES = [
  { name: "social-timeline", url: `${FRONT_BASE}/social`,         section: "Social" },
  { name: "social-agents",   url: `${FRONT_BASE}/social/agents`,  section: "Social" },
  { name: "social-create",   url: `${FRONT_BASE}/social/create`,  section: "Social" },
  { name: "lab-population",  url: `${FRONT_BASE}/lab`,            section: "Lab"    },
  { name: "lab-network",     url: `${FRONT_BASE}/lab/network`,    section: "Lab"    },
  { name: "lab-news",        url: `${FRONT_BASE}/lab/news`,       section: "Lab"    },
  { name: "lab-runs",        url: `${FRONT_BASE}/lab/runs`,       section: "Lab"    },
  { name: "about",           url: `${FRONT_BASE}/lab/about`,      section: "Lab"    },
];

const API_CHECKS = [
  { name: "arcade run",    path: "/arcade/run"    },
  { name: "runs list",     path: "/runs/"         },
  { name: "agents list",   path: "/agents/"       },
  { name: "sim status",    path: "/sim/status"    },
];

// ── Helpers ──────────────────────────────────────────────────────────────────

function httpGet(url, timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith("https") ? https : http;
    const req = lib.get(url, { timeout: timeoutMs }, (res) => {
      let body = "";
      res.on("data", d => body += d);
      res.on("end", () => resolve({ status: res.statusCode, body }));
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("timeout")); });
  });
}

async function waitForBackend(maxWaitMs = 120000) {
  const start = Date.now();
  process.stdout.write("→ waiting for backend (sim/status)");
  // Phase 1: wait for the server to accept connections at all
  while (Date.now() - start < maxWaitMs) {
    try {
      const r = await httpGet(`${API_BASE}/sim/status`, 3000);
      if (r.status < 500) { process.stdout.write(" ready\n"); break; }
    } catch { /* not up yet */ }
    process.stdout.write(".");
    await new Promise(r => setTimeout(r, 1000));
    if (Date.now() - start >= maxWaitMs) { process.stdout.write(" TIMED OUT\n"); return false; }
  }
  // Phase 2: wait for arcade/run to respond (may be blocked during IPIP)
  process.stdout.write("→ waiting for arcade run endpoint");
  while (Date.now() - start < maxWaitMs) {
    try {
      const r = await httpGet(`${API_BASE}/arcade/run`, 5000);
      if (r.status < 500) { process.stdout.write(" ready\n"); return true; }
    } catch { /* still blocked */ }
    process.stdout.write(".");
    await new Promise(r => setTimeout(r, 2000));
  }
  process.stdout.write(" TIMED OUT\n");
  console.log(`
(｡•́︿•̀｡) i tried so hard and got so far...
            but in the end, the backend just wouldn't start

  → check the logs: ${require("path").join(__dirname, "logs")}/
  → i believe in you, human ♡
`);
  process.exit(1);
}

async function waitForFrontend(maxWaitMs = 30000) {
  const start = Date.now();
  process.stdout.write("→ waiting for frontend");
  while (Date.now() - start < maxWaitMs) {
    try {
      const r = await httpGet(FRONT_BASE);
      if (r.status < 500) { process.stdout.write(" ready\n"); return true; }
    } catch { /* not up yet */ }
    process.stdout.write(".");
    await new Promise(r => setTimeout(r, 500));
  }
  process.stdout.write(" TIMED OUT\n");
  console.log(`
(っ˘̩╭╮˘̩)っ the frontend never showed up...
            i refreshed so many times. so many times.

  → check the logs: ${require("path").join(__dirname, "logs")}/
  → you've got this, human ♡
`);
  process.exit(1);
}

// ── Main ─────────────────────────────────────────────────────────────────────

(async () => {
  fs.mkdirSync(SHOT_DIR, { recursive: true });

  const backendReady  = await waitForBackend();
  const frontendReady = await waitForFrontend();

  // ── API checks ──────────────────────────────────────────────────────────────
  const apiResults = [];
  for (const check of API_CHECKS) {
    try {
      const r = await httpGet(`${API_BASE}${check.path}`);
      let preview = "";
      try {
        const parsed = JSON.parse(r.body);
        if (Array.isArray(parsed)) preview = `${parsed.length} items`;
        else if (parsed && typeof parsed === "object") {
          if (parsed.id)         preview = `id=${parsed.id}`;
          if (parsed.last_tick != null) preview += ` tick=${parsed.last_tick}`;
          if (parsed.status)     preview += ` status=${parsed.status}`;
        }
      } catch { preview = r.body.slice(0, 60); }
      apiResults.push({ name: check.name, status: r.status, preview, ok: r.status < 400 });
    } catch (e) {
      apiResults.push({ name: check.name, status: "ERR", preview: e.message, ok: false });
    }
  }

  // ── Screenshots ─────────────────────────────────────────────────────────────
  const shotResults = [];
  if (frontendReady) {
    const browser = await chromium.launch();
    const page    = await browser.newPage();
    const errors  = [];
    page.on("pageerror", e => errors.push(e.message));
    await page.setViewportSize({ width: 1280, height: 900 });

    for (const { name, url, section } of PAGES) {
      errors.length = 0;
      try {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
        await page.waitForTimeout(3500);
        const file = path.join(SHOT_DIR, `${name}.png`);
        await page.screenshot({ path: file, fullPage: true });

        // Check if the page rendered content or is still loading/empty
        // Use main element or the content div — not the full body (which includes nav/footer)
        const mainText = await page.evaluate(() => {
          const el = document.querySelector("main") || document.querySelector(".main") || document.body;
          return el.innerText.trim().slice(0, 300);
        });
        const isLoading = mainText.includes("Loading") || mainText === "" || mainText.includes("Arcade not available");
        const hasError  = errors.length > 0;

        shotResults.push({ name, section, ok: !isLoading, isLoading, errors: [...errors], file });
        const icon = isLoading ? "⚠" : "✓";
        console.log(`${icon} ${name}`);
      } catch (e) {
        shotResults.push({ name, section, ok: false, isLoading: false, errors: [e.message], file: null });
        console.log(`✗ ${name}: ${e.message}`);
      }
    }
    await browser.close();
  }

  // ── Write report ─────────────────────────────────────────────────────────────
  const now = new Date().toLocaleString();
  const lines = [
    `# Synthetic Personality Lab — health report — ${now}`,
    "",
    `**Backend:** ${backendReady ? "✓ ready" : "✗ unreachable"}  `,
    `**Frontend:** ${frontendReady ? "✓ ready" : "✗ unreachable"}`,
    "",
    "## API Health",
    "",
    "| Endpoint | Status | Info |",
    "|----------|--------|------|",
    ...apiResults.map(r => `| ${r.name} | ${r.ok ? "✓" : "✗"} ${r.status} | ${r.preview} |`),
    "",
    "## Pages",
    "",
    "| Page | Section | Status |",
    "|------|---------|--------|",
    ...shotResults.map(r => `| ${r.name} | ${r.section} | ${r.ok ? "✓ rendered" : r.isLoading ? "⚠ loading" : "✗ error"} |`),
    "",
  ];

  // Console errors
  const pagesWithErrors = shotResults.filter(r => r.errors.length > 0);
  if (pagesWithErrors.length > 0) {
    lines.push("## Console Errors", "");
    for (const r of pagesWithErrors) {
      lines.push(`**${r.name}**`);
      r.errors.forEach(e => lines.push(`- ${e}`));
      lines.push("");
    }
  }

  lines.push(`## Screenshots`, "", `Saved to: \`${SHOT_DIR}\``, "");
  shotResults.filter(r => r.file).forEach(r => {
    lines.push(`- \`${r.file}\``);
  });

  fs.writeFileSync(REPORT_FILE, lines.join("\n"));
  console.log(`\nReport saved to: ${REPORT_FILE}`);
})();
