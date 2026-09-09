/**
 * Record the runbook's five-minute demo path as a video.
 *
 *   uvicorn app.main:app          # terminal 1, :8000
 *   cd frontend && npm run dev    # terminal 2, :5173
 *   cd frontend && npm run record-demo
 *
 * Writes `docs/demo/ufms-demo.webm`, and an `.mp4` beside it if an ffmpeg can be
 * found — Playwright ships one, so this normally works with nothing installed.
 *
 * Why record at all
 * -----------------
 * The demo runs from this laptop, and the runbook covers every way the *software*
 * can fail. It covers none of the ways the *room* can fail: a flat battery, a
 * missing HDMI adapter, a projector that will not sync, being asked to present
 * from the podium machine, Docker declining to start on the morning. A video is
 * the fallback for all of those at once, and it plays anywhere.
 *
 * Two things it deliberately does
 * -------------------------------
 * **It never shows the login screen.** Recording starts already signed in: the
 * token is fetched from the API directly and injected into `sessionStorage`
 * before the first paint, via an init script. No credentials are ever on camera,
 * which matters for something that may be emailed or put on a slide.
 *
 * **It moves at a human pace, not a machine's.** Every step has an explicit
 * dwell. The precision scale holds long enough to read the floor and the
 * ceiling; the ward tooltip holds open; the allocation retraction sits on screen.
 * A demo video that scrolls at Playwright's speed is useless in a room.
 */
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, renameSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

import { chromium } from "playwright";

const BASE = process.env.UFMS_URL ?? "http://localhost:5173";
const API = process.env.UFMS_API ?? "http://127.0.0.1:8000";
const EMAIL = process.env.UFMS_EMAIL ?? "demo.officer@ufms-demo.org";
const PASSWORD = process.env.UFMS_PASSWORD ?? "ufms-demo-2026";
const OUT_DIR = path.resolve(process.argv[2] ?? "../docs/demo");
const WIDTH = 1280;
const HEIGHT = 720;

// The key sessionStorage lives under. Must match src/lib/api.ts.
const TOKEN_KEY = "ufms.access_token";

const pause = (ms) => new Promise((r) => setTimeout(r, ms));

// --- 1. a token, without ever rendering the login form ---------------------
const res = await fetch(`${API}/api/v1/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
});
if (!res.ok) {
  console.error(`login failed (${res.status}). Is the API up on ${API}, and do the`);
  console.error("demo accounts exist? See docs/03-demo-runbook.md step 3.");
  process.exit(1);
}
const { access_token: token } = await res.json();

// --- 2. record ------------------------------------------------------------
mkdirSync(OUT_DIR, { recursive: true });
const raw = path.join(OUT_DIR, ".raw");
rmSync(raw, { recursive: true, force: true });

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: WIDTH, height: HEIGHT },
  deviceScaleFactor: 1,
  colorScheme: "light",
  recordVideo: { dir: raw, size: { width: WIDTH, height: HEIGHT } },
});
// Runs before any page script, so the app finds the token on its first render
// and goes straight to the watchlist.
await context.addInitScript(
  ([key, value]) => {
    try {
      sessionStorage.setItem(key, value);
    } catch {
      /* recording in a context where storage is blocked; the app will show login */
    }
  },
  [TOKEN_KEY, token],
);

const page = await context.newPage();
const problems = [];
page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
page.on("pageerror", (e) => problems.push(String(e.message)));

async function step(label, fn, dwell) {
  process.stdout.write(`  ${label} ... `);
  await fn();
  await pause(dwell);
  console.log(`${(dwell / 1000).toFixed(1)}s`);
}

console.log(`recording ${WIDTH}x${HEIGHT}`);

// Screen 1 — the watchlist. The landing screen, and the one that carries the
// argument, so it gets the most time.
await step("watchlist: load", async () => {
  await page.goto(`${BASE}/watchlist`, { waitUntil: "networkidle" });
  await page.waitForSelector("nav", { timeout: 30000 });
}, 4000);

await step("watchlist: hold on the precision scale", async () => {
  const scale = page.getByRole("img", { name: /precision@20/i });
  if (await scale.count()) await scale.scrollIntoViewIfNeeded();
}, 6500);

await step("watchlist: the ranked twenty", async () => {
  await page.mouse.wheel(0, 420);
}, 4500);

// Screen 2 — the ward index. Series, then the map, then a tooltip.
await step("ward index: load", async () => {
  await page.click('a[href="/index"]');
  await page.waitForTimeout(3000);
}, 4000);

await step("ward index: the series against the 1.00 city norm", async () => {
  await page.mouse.wheel(0, 300);
}, 4500);

await step("ward index: the choropleth", async () => {
  await page.mouse.wheel(0, 400);
}, 4000);

await step("ward index: hover a ward for name, index and quarter", async () => {
  const wards = page.locator(".leaflet-overlay-pane path");
  if (await wards.count()) {
    // A ward near the middle of the city rather than feature 0, which sits at
    // the northern edge and puts the tooltip half off-screen.
    await wards.nth(Math.floor((await wards.count()) / 2)).hover();
  }
}, 5000);

// Screen 3 — emerging. The honest one; the banner needs to be readable.
await step("emerging: load", async () => {
  await page.click('a[href="/emerging"]');
  await page.waitForTimeout(2500);
}, 4500);

await step("emerging: the no-ground-truth banner and the caveats", async () => {
  await page.mouse.wheel(0, 380);
}, 5500);

// Screen 4 — allocation. The retraction sits on screen deliberately.
await step("allocation: load", async () => {
  await page.click('a[href="/allocation"]');
  await page.waitForTimeout(2500);
}, 4000);

await step("allocation: the retraction, in full", async () => {
  await page.mouse.wheel(0, 260);
}, 6500);

await step("allocation: both scatter panels, no trend line", async () => {
  await page.mouse.wheel(0, 420);
}, 6000);

await step("back to the watchlist to close", async () => {
  await page.click('a[href="/watchlist"]');
  await page.waitForTimeout(1500);
}, 3000);

// --- 3. name it, and transcode -------------------------------------------
// The video is only finalised when the context closes, and `saveAs` needs the
// browser still alive - so the order here is: close context, save, close browser.
const video = page.video();
const webm = path.join(OUT_DIR, "ufms-demo.webm");
rmSync(webm, { force: true });

await context.close();
if (video) {
  await video.saveAs(webm);
}
await browser.close();

if (!existsSync(webm)) {
  const found = readdirSync(raw).find((f) => f.endsWith(".webm"));
  if (!found) {
    console.error("no video was produced");
    process.exit(1);
  }
  renameSync(path.join(raw, found), webm);
}
rmSync(raw, { recursive: true, force: true });

const { size } = await import("node:fs").then((fs) => fs.statSync(webm));
console.log(`\n${path.relative(process.cwd(), webm)}  ${(size / 1024 / 1024).toFixed(2)} MB`);

/**
 * Find an ffmpeg that can actually encode H.264.
 *
 * The check matters. **Playwright's bundled ffmpeg cannot** — it is a minimal
 * build carrying only libvpx (VP8) and png, which is all it needs to record. Use
 * it blindly and the transcode fails with a wall of configure flags, or worse
 * succeeds into a format nothing plays. So each candidate is asked what encoders
 * it has, and rejected unless libx264 is among them.
 */
function findFfmpeg() {
  const candidates = [];
  if (process.env.FFMPEG) candidates.push(process.env.FFMPEG);
  candidates.push("ffmpeg"); // PATH
  candidates.push(
    "C:\\Program Files\\DownloadHelper CoApp\\ffmpeg.exe",
    "C:\\ffmpeg\\bin\\ffmpeg.exe",
    path.join(homedir(), "scoop", "shims", "ffmpeg.exe"),
    "C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe",
  );
  for (const c of candidates) {
    try {
      const out = execFileSync(c, ["-hide_banner", "-encoders"], {
        stdio: ["ignore", "pipe", "ignore"],
      }).toString();
      if (out.includes("libx264")) return c;
    } catch {
      /* not present, or not runnable; try the next */
    }
  }
  return null;
}

const ffmpeg = findFfmpeg();
const mp4 = path.join(OUT_DIR, "ufms-demo.mp4");
if (!ffmpeg) {
  console.log("\nNO H.264-CAPABLE FFMPEG FOUND, so only the .webm exists.");
  console.log("Playwright's bundled ffmpeg carries VP8 only and cannot make an mp4.");
  console.log("A projector laptop may have nothing that plays webm, so before");
  console.log("relying on this as the fallback, install ffmpeg and re-run:");
  console.log("    winget install Gyan.FFmpeg");
  console.log("    npm run record-demo");
  console.log("A browser will play the webm; PowerPoint will not embed it.");
} else {
  rmSync(mp4, { force: true });
  console.log(`transcoding to mp4 with ${path.basename(ffmpeg)} ...`);
  try {
    execFileSync(ffmpeg, [
      "-y", "-i", webm,
      // H.264 + yuv420p + faststart: the combination that plays on a stock
      // Windows install, PowerPoint, and QuickTime without a codec pack.
      "-c:v", "libx264", "-preset", "slow", "-crf", "28",
      "-pix_fmt", "yuv420p", "-movflags", "+faststart",
      "-an", mp4,
    ], { stdio: ["ignore", "ignore", "pipe"] });
    const m = (await import("node:fs")).statSync(mp4);
    console.log(`${path.relative(process.cwd(), mp4)}  ${(m.size / 1024 / 1024).toFixed(2)} MB`);
  } catch (e) {
    console.error("transcode failed:", String(e.stderr ?? e).slice(0, 500));
    console.error("The .webm is still valid.");
  }
}

if (problems.length) {
  console.error(`\n${problems.length} console error(s) during recording:`);
  for (const p of problems.slice(0, 5)) console.error(`  ${p}`);
  process.exit(1);
}
console.log("\nno console errors during the recording");
