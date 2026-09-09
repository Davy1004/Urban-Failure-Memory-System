# UFMS — frontend

The four dashboard screens, on the five read-only endpoints served by the API
in the parent directory. This is an npm project *inside* the backend repository
(`frontend/`), not a sibling of it — every path below is relative to this file.

React 19 + Vite + Tailwind v4 + Recharts + Leaflet. Components are written in
the shadcn idiom — owned by this repo under `src/components/ui`, not pulled from
a package.

## Running it

The API has to be up first, with its derived tables built:

```bash
cd ..                                   # the repository root
docker compose up -d
alembic upgrade head
python -m app.ingestion.cli derive      # builds the four derived tables
uvicorn app.main:app --reload           # serves on :8000
```

Then, back in this directory:

```bash
cd frontend
npm install
npm run dev                             # :5173, proxies /api to :8000
```

`npm run build` type-checks and bundles; `npm test` runs the contract tests.

Officers do not self-register. Create an account with the snippet in the backend
README, or promote an existing row.

## The visual check, and Playwright

`npm run visual-check` walks all four screens at 390, 768 and 1360 px wide and
fails on a console error or a horizontal scroll. It found five real defects on
its first run, none of them reachable from the DOM, which is the class of bug the
25-test contract suite cannot see — so it is kept.

It drives a real browser, and **Playwright's browser binary is not installed by
`npm install`.** On a new machine, once:

```bash
npx playwright install chromium
```

Without it both `npm run visual-check` and `npm run figures` fail immediately
with a message about a missing executable. That is a missing browser, not a
broken check. It is deliberately not wired into CI this week.

`npm run figures` uses the same browser to render the paper figures into
`../docs/figures/`, against a running dev server — so every number in a figure
is the number the API served, not a redrawing.

## The ward boundaries

`public/bbmp-wards.geojson` is generated, not hand-maintained:

```bash
cd ..
python scripts/export_ward_geojson.py
```

It writes straight to `frontend/public/bbmp-wards.geojson`; both ends of that
path are now inside one repository, so there is no cross-project write.

It reads `bbmp_ward_map_2015.kml` — the 198-ward delimitation the ward crosswalk
was built on, so `ward_no` joins straight onto the API's rows. The 2022 KML is a
different delimitation and will not join. The exporter fails loudly if it does
not find exactly 198 wards, because a ward missing from a choropleth reads as
"nothing happened here" rather than "no data".

## What the screens are required to show

This is the part to read before changing anything. Each of these is a
presentation rule the analysis paid for, and each is pinned by a test in
`src/test/screens.test.tsx`.

**Watchlist.** `precision@20` is drawn as a mark on a scale that ends at the
oracle ceiling, with the random floor as a region of the track — never as a stat
tile. 14.08% on its own reads as a failed model; against a 4.79% chance floor and
a 37.72% ceiling it is 37% of everything achievable. A caption saying that can be
dropped in a redesign, but a mark cannot be drawn without its scale, so the
context is structural rather than adjacent. The screen calls itself a *standing
watchlist* and never a prediction or a forecast.

**Ward index.** The `rel = 1.00` reference line and the diverging midpoint on the
map are the same fact drawn twice, and neither is optional. Complaint volume
roughly doubled 2021–2024, so an un-benchmarked series shows reporting growth and
reads as flooding. The map bins on ratio (×/÷ 1.41), not on difference.

**Emerging.** The label is *chronically above norm*. The word "accelerating"
appears on this screen only in the caveat that rules it out — flagged wards do
not significantly exceed their own first-half level (Wilcoxon signed-rank,
p = 0.116). `ground_truth_available: false` is shown as a banner: BBMP's register
carries no listing years, so no flag here has been or can be validated against
the city's own additions.

**Allocation.** Two scatter panels side by side — spend against ward area, spend
against flooding need — because the difference between them *is* the finding.
No fitted line anywhere, and no chart plots spend against the change in index:
the dose-response is retracted and no outcome design is identifiable on this
data. The `retraction` field is rendered in full.

**Everywhere.** Empty states say what is missing and how to produce it. Nothing
substitutes a plausible number for an absent one.

## Colour

`src/index.css` holds the palette as CSS custom properties, light and dark. Every
value was checked with the data-viz palette validator before use:

| Slots | Mode | Result |
|---|---|---|
| `#2a78d6 #eb6834 #1baf7a` | light, all-pairs | PASS |
| `#3987e5 #d95926 #199e70` | dark, all-pairs | PASS |
| cool arm `#86b6ef #2a78d6 #184f95` | light, ordinal | PASS (2.06:1) |
| warm arm `#ec958c #d94a4a #9b302f` | light, ordinal | PASS (2.21:1) |
| cool arm `#184f95 #3987e5 #9ec5f4` | dark, ordinal | PASS (2.15:1) |
| warm arm `#8f2d2a #d04b47 #e8938a` | dark, ordinal | PASS (2.14:1) |

The choropleth is diverging (blue↔red, neutral gray midpoint) because 1.00 is a
real midpoint. Sequential would make an ordinary ward look like a mild version of
a bad one. Status colours are reserved and always ship with an icon and a label.

## Deploying

Vercel, static. `npm run build` emits `dist/`. Point `/api` at the deployed API
with a rewrite; the dev proxy in `vite.config.ts` is the local equivalent.
