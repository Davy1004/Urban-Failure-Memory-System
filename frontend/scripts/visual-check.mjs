/**
 * A visual smoke check against a running dev server.
 *
 *   npm run dev                                   # in one terminal
 *   node scripts/visual-check.mjs [outDir] [light|dark]
 *
 * Not a screenshot-diff harness. It signs in, walks the four screens at three
 * widths, and fails on the three things a unit test cannot see:
 *
 *   - a console error or a failed request,
 *   - the page scrolling sideways at 390px,
 *   - and it writes full-page screenshots so a human can look at them.
 *
 * It earned its keep on the first run: the basemap provider had started
 * watermarking every tile with "API KEY REQUIRED", the meter's chance zone was
 * hidden underneath its own fill, a reference-line label sat on top of the
 * series, long ward names were clipped, and the header overflowed by 182px on a
 * phone. None of those is visible from the DOM.
 *
 * Needs `npx playwright install chromium` once.
 */
import { chromium } from "playwright";

const BASE = process.env.UFMS_URL ?? "http://localhost:5173";
const EMAIL = process.env.UFMS_EMAIL ?? "demo.officer@ufms-demo.org";
const PASSWORD = process.env.UFMS_PASSWORD ?? "ufms-demo-2026";
const OUT = process.argv[2] ?? "./screenshots";
const THEME = process.argv[3] === "dark" ? "dark" : "light";

const SCREENS = [
  ["watchlist", "/watchlist"],
  ["index", "/index"],
  ["emerging", "/emerging"],
  ["allocation", "/allocation"],
];
const WIDTHS = [390, 768, 1360];

const problems = [];

async function signIn(page) {
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.fill("#email", EMAIL);
  await page.fill("#password", PASSWORD);
  await page.click("button[type=submit]");
  await page.waitForSelector("nav", { timeout: 15000 });
}

for (const width of WIDTHS) {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width, height: 1000 },
    colorScheme: THEME,
  });
  page.on("console", (m) => {
    if (m.type() === "error") problems.push(`${width}px console: ${m.text()}`);
  });
  page.on("pageerror", (e) => problems.push(`${width}px pageerror: ${e.message}`));
  page.on("requestfailed", (r) =>
    problems.push(`${width}px requestfailed: ${r.url()}`),
  );

  // Client-side navigation, never page.goto: the token lives in memory only,
  // so a full reload signs the session out. That is intended behaviour.
  await signIn(page);
  for (const [name, href] of SCREENS) {
    await page.click(`nav a[href="${href}"]`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(href === "/index" ? 3000 : 700);

    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    if (overflow > 2) {
      problems.push(`${width}px ${name}: page scrolls sideways by ${overflow}px`);
    }
    if (width === WIDTHS.at(-1)) {
      await page.screenshot({ path: `${OUT}/${THEME}-${name}.png`, fullPage: true });
    }
  }
  await browser.close();
  console.log(`${width}px ${THEME}: checked`);
}

if (problems.length) {
  console.error("\nPROBLEMS:");
  for (const p of problems) console.error(" -", p);
  process.exit(1);
}
console.log(`\nno console errors, no failed requests, no horizontal overflow`);
console.log(`screenshots in ${OUT}/`);
