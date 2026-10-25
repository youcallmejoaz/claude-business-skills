// Records every clip in the shot list as an MP4 (1920x1080, 30 fps, H.264, yuv420p, no audio).
//
//   node clips/record.mjs            # all clips
//   node clips/record.mjs C02 K01    # just these
//
// Starts Skills Studio in demo mode with the seeded sample data, drives it with scripted
// user actions (visible cursor, a ring on every click, typing at about 12 characters a
// second), records one video per scene, trims dead time and converts with ffmpeg.
// Cards (K) and prompt replays (P) are local HTML pages in clips/cards/.

import { spawn, spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const RAW = path.join(HERE, "raw");
const PORT = 8765;
const BASE = `http://127.0.0.1:${PORT}`;
const W = 1920, H = 1080;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const PAUSE = 750;          // after each action
const TYPE_DELAY = 83;      // ms per character, about 12 characters a second

const CURSOR_JS = `(() => {
  if (window.__cursorInstalled) return; window.__cursorInstalled = true;
  const install = () => {
    const c = document.createElement('div'); c.id = '__cursor';
    c.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M5 2.5l14 8.2-6.3 1.6-3 6.2z" fill="#14201b" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, {position:'fixed', zIndex:2147483647, pointerEvents:'none', marginLeft:'-5px', marginTop:'-3px', filter:'drop-shadow(0 2px 3px rgba(0,0,0,.25))'});
    const p = JSON.parse(sessionStorage.getItem('__cursor') || '[960,600]');
    c.style.left = p[0] + 'px'; c.style.top = p[1] + 'px';
    document.documentElement.appendChild(c);
    addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px';
      sessionStorage.setItem('__cursor', JSON.stringify([e.clientX, e.clientY])); }, true);
    addEventListener('mousedown', e => {
      const r = document.createElement('div');
      Object.assign(r.style, {position:'fixed', left:(e.clientX-24)+'px', top:(e.clientY-24)+'px', width:'48px', height:'48px',
        border:'4px solid #1f7a4d', borderRadius:'50%', zIndex:2147483646, pointerEvents:'none', opacity:'1',
        transition:'transform .55s ease-out, opacity .55s ease-out', background:'rgba(31,122,77,.12)'});
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => requestAnimationFrame(() => { r.style.transform = 'scale(1.8)'; r.style.opacity = '0'; }));
      setTimeout(() => r.remove(), 700);
    }, true);
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', install); else install();
})();`;

// ------------------------------------------------------------------ helpers

class Actor {
  constructor(page) { this.page = page; this.x = 960; this.y = 600; }
  async glide(x, y, ms = 650) {
    const sx = this.x, sy = this.y, n = Math.max(12, Math.round(ms / 16));
    for (let i = 1; i <= n; i++) {
      const t = i / n, e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      await this.page.mouse.move(sx + (x - sx) * e, sy + (y - sy) * e);
      await sleep(ms / n);
    }
    this.x = x; this.y = y;
  }
  async to(selector, opts = {}) {
    const el = this.page.locator(selector).first();
    await el.scrollIntoViewIfNeeded();
    const b = await el.boundingBox();
    const x = b.x + (opts.dx ?? b.width / 2), y = b.y + (opts.dy ?? b.height / 2);
    await this.glide(x, y, opts.ms ?? 650);
    return b;
  }
  async click(selector, opts = {}) {
    await this.to(selector, opts);
    await sleep(180);
    await this.page.mouse.down(); await sleep(90); await this.page.mouse.up();
    await sleep(opts.after ?? PAUSE);
  }
  async type(selector, text) {
    await this.click(selector, { after: 300 });
    await this.page.keyboard.type(text, { delay: TYPE_DELAY });
    await sleep(PAUSE);
  }
  async scrollTo(top, ms = 1100) {
    await this.page.evaluate((t) => window.scrollTo({ top: t, behavior: "smooth" }), top);
    await sleep(ms);
  }
  async scrollToEl(selector, offset = 90, ms = 1100) {
    const top = await this.page.evaluate(([s, o]) => {
      const el = document.querySelector(s); return el.getBoundingClientRect().top + window.scrollY - o;
    }, [selector, offset]);
    await this.scrollTo(top, ms);
  }
}

async function startServer() {
  const py = path.join(ROOT, ".venv", "bin", "python");
  const proc = spawn(py, ["-m", "uvicorn", "studio.app:app", "--host", "127.0.0.1", "--port", String(PORT)], {
    cwd: ROOT, env: { ...process.env, DEMO_MODE: "1", AS_OF_DATE: "2026-10-23" }, stdio: "ignore",
  });
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(`${BASE}/health`); if (r.ok) return proc; } catch { /* not up yet */ }
    await sleep(250);
  }
  proc.kill(); throw new Error("Skills Studio did not start");
}

function ffmpeg(args) {
  const r = spawnSync("ffmpeg", ["-y", "-loglevel", "error", ...args], { stdio: "inherit" });
  if (r.status !== 0) throw new Error("ffmpeg failed: " + args.join(" "));
}

function even(n) { return Math.round(n / 2) * 2; }

// Convert one raw recording to the final MP4, trimming dead time at both ends.
function finish(id, name, raw, startSec, durSec, crop) {
  const out = path.join(HERE, `${id}_${name}.mp4`);
  let vf = "fps=30";
  if (crop) {
    vf = `crop=${even(crop.w)}:${even(crop.h)}:${even(crop.x)}:${even(crop.y)},scale=${W}:${H}:flags=lanczos,fps=30`;
  } else {
    vf = `scale=${W}:${H}:flags=lanczos,fps=30`;
  }
  ffmpeg(["-ss", startSec.toFixed(2), "-i", raw, "-t", durSec.toFixed(2), "-vf", `${vf},format=yuv420p`,
          "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-movflags", "+faststart", "-an", out]);
  return out;
}

// A 16:9 box around a region (viewport coordinates), padded, kept inside the frame.
function box16x9(r, pad = 60, minW = 900) {
  let w = Math.max(r.w + pad * 2, minW), h = w * 9 / 16;
  if (h < r.h + pad * 2) { h = r.h + pad * 2; w = h * 16 / 9; }
  w = Math.min(w, W); h = Math.min(h, H);
  let x = r.x + r.w / 2 - w / 2, y = r.y + r.h / 2 - h / 2;
  x = Math.max(0, Math.min(W - w, x)); y = Math.max(0, Math.min(H - h, y));
  return { x, y, w, h };
}

function union(a, b) {
  const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
  return { x, y, w: Math.max(a.x + a.width, b.x + b.width) - x, h: Math.max(a.y + a.height, b.y + b.height) - y };
}

// ------------------------------------------------------------------ scenes
// Each scene gets a fresh page that is already recording. It returns
// { start } (ms since recording began when the action starts) and optionally a crop box.

const W43 = "production_2026-W43.xlsx";
const W43_PATH = path.join(ROOT, "data", "production", W43);

const SCENES = {
  async C01(page, a, clock) {
    await page.goto(`${BASE}/skills/production-report`); await page.waitForLoadState("networkidle");
    await sleep(400);
    const start = clock();
    await sleep(600);
    await a.to(".drop", { ms: 900 }); await sleep(300);
    // A file dragged from the desktop: show the drop state, then hand the file to the page.
    await page.locator(".drop").evaluate((el) => el.classList.add("over"));
    await sleep(900);
    await page.setInputFiles(".drop input[type=file]", W43_PATH);
    await page.locator(".drop").evaluate((el) => el.classList.remove("over"));
    await sleep(1200);
    await a.to("#run-btn", { ms: 900 }); await sleep(900);
    return { start, end: clock() + 300 };
  },

  async C02(page, a, clock) {
    await page.goto(`${BASE}/skills/production-report`); await page.waitForLoadState("networkidle");
    await page.setInputFiles(".drop input[type=file]", W43_PATH);
    await a.glide(1300, 330, 10); await sleep(300);
    const start = clock();
    await sleep(500);
    await a.click("#run-btn", { after: 400 });
    await page.waitForSelector("#narrative");
    await sleep(500);
    await a.scrollToEl("#numbers", 24, 1200);
    await sleep(500);
    await a.to("#row-grant_fowler", { dx: 300, ms: 900 }); await sleep(1000);
    await a.to("#narrative .headline", { dx: 200, ms: 900 }); await sleep(1300);
    await a.to("#narrative .narr p:nth-child(2)", { dx: 400, ms: 800 }); await sleep(1300);
    return { start, end: clock() + 200 };
  },

  async C03(page, a, clock) {
    await page.goto(`${BASE}/skills/production-report`); await page.waitForLoadState("networkidle");
    await page.selectOption("#sample", W43);
    await page.click("#run-btn"); await page.waitForSelector("#narrative");
    await sleep(600);
    await page.evaluate(() => { const el = document.querySelector("#numbers"); window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 24); });
    await sleep(500);
    const flag = await page.locator("#flag-below_target_grant_fowler").boundingBox();
    await a.glide(flag.x + flag.width - 60, flag.y + flag.height + 70, 10);
    await sleep(300);
    const start = clock();
    await sleep(700);
    await a.to("#flag-below_target_grant_fowler", { dx: flag.width - 70, dy: flag.height - 18, ms: 900 });
    await sleep(2600);
    const r = { x: flag.x, y: flag.y, w: flag.width, h: flag.height };
    return { start, end: clock() + 300, crop: box16x9(r, 60, 1100) };
  },

  async C04(page, a, clock) {
    await page.goto(`${BASE}/skills/weekly-owner-brief`); await page.waitForLoadState("networkidle");
    await page.selectOption("#sample", W43);
    await a.glide(1300, 330, 10); await sleep(300);
    const start = clock();
    await sleep(400);
    await a.click("#run-btn", { after: 300 });
    await page.waitForSelector("#viewer img");
    await sleep(500);
    await a.scrollToEl("#viewer", 110, 1200);
    await a.to("#viewer", { dy: 300, ms: 700 });
    for (let i = 0; i < 6; i++) { await page.mouse.wheel(0, 110); await sleep(260); }
    await sleep(800);
    await a.to("#email-body", { dx: 260, dy: 60, ms: 1000 });
    await sleep(2200);
    return { start, end: clock() + 200 };
  },

  async C05(page, a, clock) {
    await page.goto(`${BASE}/skills/quote-intake`); await page.waitForLoadState("networkidle");
    const email = fs.readFileSync(path.join(ROOT, "data", "quote_emails", "q01_bundle_auto_home.txt"), "utf8");
    await a.glide(700, 600, 10); await sleep(300);
    const start = clock();
    await sleep(400);
    await a.click("#email", { dy: 80, after: 400 });
    // Paste, as a person would with Ctrl+V.
    await page.locator("#email").fill(email);
    await sleep(1300);
    await a.click("#run-btn", { after: 300 });
    await page.waitForSelector("#quote-fields");
    await sleep(1500);
    await a.to("#quote-fields tr:nth-child(4) input", { ms: 900 }); await sleep(1100);
    await a.scrollToEl("#missing", 300, 1400);
    await a.to("#missing li", { dx: 120, ms: 900 }); await sleep(1600);
    return { start, end: clock() + 200 };
  },

  async C06(page, a, clock) {
    await page.goto(`${BASE}/skills/customer-reply`); await page.waitForLoadState("networkidle");
    const msg = fs.readFileSync(path.join(ROOT, "data", "customer_messages", "m01_saturday_hours.txt"), "utf8");
    await page.locator("#message").fill(msg);
    await page.click("#run-btn"); await page.waitForSelector("#reply");
    await sleep(600);
    const chip = page.locator('.cite[data-id="FAQ-08"]').last();
    const sent = await chip.locator("xpath=..").boundingBox();
    const src = await page.locator("#src-FAQ-08").boundingBox();
    await a.glide(sent.x + sent.width / 2, sent.y - 60, 10); await sleep(300);
    const start = clock();
    await sleep(600);
    await a.click('.cite[data-id="FAQ-08"] >> nth=-1', { after: 2600 });
    const crop = box16x9(union(sent, src), 50, 1100);
    return { start, end: clock() + 400, crop };
  },

  async C07(page, a, clock) {
    await page.goto(`${BASE}/evals`); await page.waitForLoadState("networkidle");
    await a.glide(600, 500, 10); await sleep(300);
    const start = clock();
    await sleep(500);
    await a.click("#run-btn", { after: 300 });
    await page.waitForSelector("#eval-results");
    await sleep(1200);
    await a.to("#eval-results .big", { ms: 800 }); await sleep(1000);
    await a.scrollTo(260, 1300);
    await a.to("#eval-results table tr:last-child td:last-child", { ms: 900 }); await sleep(1600);
    return { start, end: clock() + 200 };
  },

  async C08(page, a, clock) {
    await page.goto(`${BASE}/connector`); await page.waitForLoadState("networkidle");
    await a.glide(700, 500, 10); await sleep(300);
    const start = clock();
    await sleep(400);
    await a.type("#question", "show open quotes older than 7 days");
    await a.click("#ask-btn", { after: 300 });
    await page.waitForSelector("#tool-table");
    await sleep(900);
    await a.to(".call", { dx: 220, ms: 800 }); await sleep(1200);
    await a.to("#tool-table tr:nth-child(3)", { dx: 600, ms: 900 }); await sleep(1700);
    return { start, end: clock() + 200 };
  },
};

// Cards and prompt replays: a page that plays its own animation for `duration` seconds.
const CARDS = {
  K01: { file: "K01_problem.html", name: "problem", duration: 6.5 },
  K02: { file: "K02_flow.html", name: "flow", duration: 8.5 },
  K03: { file: "K03_safeguards.html", name: "safeguards", duration: 7.5 },
  K04: { file: "K04_offer.html", name: "offer", duration: 7.5 },
  P01: { file: "P01_setup_prompt.html", name: "setup_prompt", duration: 10.5, prompt: true },
  P02: { file: "P02_skill_prompt.html", name: "skill_prompt", duration: 9, prompt: true },
};
const NAMES = { C01: "upload", C02: "report", C03: "flag_closeup", C04: "owner_brief", C05: "quote_intake",
                C06: "citation_closeup", C07: "evals", C08: "connector" };

// ------------------------------------------------------------------ main

async function recordScene(browser, id, run, { cursor = true } = {}) {
  const dir = path.join(RAW, id);
  fs.rmSync(dir, { recursive: true, force: true });
  const context = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1,
                                             recordVideo: { dir, size: { width: W, height: H } } });
  if (cursor) await context.addInitScript(CURSOR_JS);
  const page = await context.newPage();
  const t0 = Date.now();
  const clock = () => Date.now() - t0;
  const a = new Actor(page);
  const res = await run(page, a, clock);
  const video = page.video();
  await context.close();
  const raw = path.join(RAW, `${id}.webm`);
  fs.renameSync(await video.path(), raw);
  fs.rmSync(dir, { recursive: true, force: true });
  return { raw, ...res };
}

async function main() {
  const only = process.argv.slice(2);
  const want = (id) => !only.length || only.includes(id);
  fs.mkdirSync(RAW, { recursive: true });
  const browser = await chromium.launch();
  let server = null;
  try {
    if (Object.keys(SCENES).some(want)) server = await startServer();
    for (const [id, run] of Object.entries(SCENES)) {
      if (!want(id)) continue;
      const r = await recordScene(browser, id, run);
      const dur = (r.end - r.start) / 1000;
      const out = finish(id, NAMES[id], r.raw, r.start / 1000, dur, r.crop);
      console.log(`${id} ${path.basename(out)} ${dur.toFixed(1)}s${r.crop ? " (close-up)" : ""}`);
    }
    for (const [id, card] of Object.entries(CARDS)) {
      if (!want(id)) continue;
      const url = pathToFileURL(path.join(HERE, "cards", card.file)).href;
      const r = await recordScene(browser, id, async (page, a, clock) => {
        await page.goto(url + "?wait=1"); await page.waitForLoadState("load");
        await page.evaluate(() => document.fonts.ready);
        await sleep(300);
        const start = clock();
        await page.evaluate(() => window.play && window.play());
        await sleep(card.duration * 1000);
        await page.screenshot({ path: path.join(HERE, "cards", `${id}.png`) });
        return { start, end: start + card.duration * 1000 };
      }, { cursor: false });
      const out = finish(id, card.name, r.raw, r.start / 1000, card.duration, null);
      console.log(`${id} ${path.basename(out)} ${card.duration.toFixed(1)}s`);
    }
  } finally {
    await browser.close();
    if (server) server.kill();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
