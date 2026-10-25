// Renders the two cover layouts: 1600x1200, 1000x750 and a 400x300 preview of each.
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const HERE = path.dirname(fileURLToPath(import.meta.url));
const DOCS = path.resolve(HERE, "..");
const browser = await chromium.launch();
for (const v of ["a", "b"]) {
  for (const [w, suffix, scale] of [[1600, "", 1], [1000, "-1000", 0.625], [400, "-preview-400", 0.25]]) {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: scale });
    await page.goto(pathToFileURL(path.join(HERE, `cover-${v}.html`)).href, { waitUntil: "networkidle" });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(DOCS, `upwork-cover-${v}${suffix}.png`) });
    await page.close();
  }
}
await browser.close();
