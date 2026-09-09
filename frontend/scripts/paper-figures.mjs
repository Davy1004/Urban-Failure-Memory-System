/**
 * Figures for the paper.
 *
 *   npm run dev                          # in one terminal
 *   node scripts/paper-figures.mjs [outDir]
 *
 * Writes the four screens full-page plus four cropped figures at 2x, into
 * `../docs/figures/` by default. Every figure is rendered from the
 * live API against the loaded database, so nothing in them is mocked or
 * redrawn — the number in a figure is the number the system serves.
 *
 * Deterministic by construction: the derived tables are rebuilt from fixed
 * windows, so re-running this produces the same figures until the data changes.
 *
 * Needs `npx playwright install chromium` once.
 */
import { chromium } from "playwright";

const BASE = process.env.UFMS_URL ?? "http://localhost:5173";
const EMAIL = process.env.UFMS_EMAIL ?? "demo.officer@ufms-demo.org";
const PASSWORD = process.env.UFMS_PASSWORD ?? "ufms-demo-2026";
const OUT = process.argv[2] ?? "../docs/figures";

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1360, height: 1000 },
  // 2x so a figure survives being dropped into a two-column paper.
  deviceScaleFactor: 2,
  colorScheme: "light",
});

await page.goto(BASE, { waitUntil: "networkidle" });
await page.fill("#email", EMAIL);
await page.fill("#password", PASSWORD);
await page.click("button[type=submit]");
await page.waitForSelector("nav", { timeout: 15000 });

const written = [];
async function shot(name, locator, caption) {
  await locator.screenshot({ path: `${OUT}/${name}.png` });
  written.push([name, caption]);
  console.log(`  ${name}.png — ${caption}`);
}
async function fullPage(name, caption) {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  written.push([name, caption]);
  console.log(`  ${name}.png — ${caption}`);
}

const card = (heading) =>
  page
    .locator("h2", { hasText: heading })
    .locator("xpath=ancestor::div[contains(@class,'rounded-lg')][1]");

// --- Watchlist -------------------------------------------------------------
console.log("watchlist:");
await page.click('nav a[href="/watchlist"]');
await page.waitForLoadState("networkidle");
await page.waitForTimeout(800);
await shot(
  "fig-precision-scale",
  page.locator("figure").first(),
  "precision@20 = 14.08% between a 4.79% chance floor and a 37.72% oracle ceiling",
);
await fullPage("screen-watchlist", "Screen 2, the standing watchlist");

// --- Ward index, Jakkur ----------------------------------------------------
console.log("ward index (Jakkur):");
await page.click('nav a[href="/index"]');
await page.waitForLoadState("networkidle");
await page.waitForTimeout(1200);
await page.fill('input[type="search"]', "Jakkur");
await page.click('button[role="option"]:has-text("Jakkur")');
await page.waitForTimeout(1500);
await shot(
  "fig-jakkur-index",
  card("relative flooding index"),
  "Jakkur's relative flooding index over 20 quarters, against the city norm",
);
await page.waitForTimeout(2500);
await shot(
  "fig-ward-choropleth",
  card("Every ward, latest quarter"),
  "All 198 wards by relative index, 2025Q1, diverging about the city norm",
);
await fullPage("screen-index", "Screen 1, the ward index");

// --- Emerging --------------------------------------------------------------
console.log("emerging:");
await page.click('nav a[href="/emerging"]');
await page.waitForLoadState("networkidle");
await page.waitForTimeout(900);
await shot(
  "fig-level-persistence",
  card("means"),
  "Flagged wards, first half to second half: they stay above the norm rather than accelerating",
);
await fullPage("screen-emerging", "Screen 3, the emerging watch");

// --- Allocation ------------------------------------------------------------
console.log("allocation:");
await page.click('nav a[href="/allocation"]');
await page.waitForLoadState("networkidle");
await page.waitForTimeout(900);
await shot(
  "fig-allocation-scatter",
  card("What spend tracks"),
  "Drainage spend against ward area and against relative flooding need — the allocation finding",
);
await fullPage("screen-allocation", "Screen 4, allocation");

await browser.close();
console.log(`\n${written.length} figures written to ${OUT}/`);
