# Report — the frontend, the figures, and three doc corrections

**Date:** 9 September 2026
**Task:** NEXT.md, "the frontend" (revised mid-task to "frontend, and it is now
secondary" once the 16 September progress evaluation was confirmed)
**Status:** complete. The frontend is finished, not partial. 143 backend tests
and 25 frontend tests pass.

---

## 1. Read this first if you are short of time

**The frontend is done, so the fallback in your revision is not needed.** All
four screens work against the real API. You wrote "if the screens are not
finished by the 16th, demonstrate the API through `/docs`" — they are finished,
and there are screenshots to prove it.

**The figures you asked for are in `docs/figures/`**, nine of them at 2×,
rendered from the live system against the loaded database. `docs/figures/README.md`
lists what each shows and the exact numbers in it. The three you named
specifically:

- `fig-jakkur-index.png` — Jakkur's index **0.22 (2020Q2) → 1.64 (2025Q1)**,
  mean 1.09, above the norm in 10 of 20 quarters. The ₹494 M case study.
- `fig-allocation-scatter.png` — spend vs area beside spend vs relative need,
  **ρ = +0.474** against **+0.082 (p = 0.392)**, no fitted line on either.
- `screen-*.png` — all four screens, full page.

**Two caption warnings, repeated in that README because they are the kind of
thing a paper gets wrong under deadline:** the precision figure must never be
quoted without its floor and ceiling (that is the entire point of the figure),
and the allocation scatter must never be given a trend line (the dose-response
is retracted, and a line through a scatter reads as an effect estimate whatever
the caption says).

**I did not write any of the paper.** You said it is being drafted in the
planning session and that two versions would diverge. Agreed and left alone.

---

## 2. Your Screen 2 instruction was right, and it went further than expected

You wrote: *"a caveat sitting beside a number can be dropped in a redesign, but a
mark cannot be drawn without its scale."*

That is now literally true of the code. `PrecisionScale` takes `achieved`,
`ceiling` and `floor` as **required** props, the axis domain is `[0, ceiling]`,
and the floor is a region of the track. There is no way to render it with a
number and no context — a missing prop is a type error, and a removed reference
point is a broken drawing rather than a weakened claim.

**And it caught a bug that a response field never would have.** My first version
filled the bar from zero to 14.08% in the accent colour and drew the chance zone
underneath it. On screen the chance region was completely hidden by its own
fill: the *label* "4.79% chance" survived, the *region* did not. The bar now
splits at the floor — grey from 0 to 4.79% (what chance gets you, so it is not
coloured as an achievement), accent from 4.79% to 14.08% (what memory adds),
light track to the 37.72% ceiling. That reads correctly and it was only visible
in a screenshot.

I also took the second half of your answer: `npm test` includes DOM assertions
that all three figures appear in the rendered output, that they are ordered
floor < achieved < ceiling, and — the case I think matters most — that an
**unscored** snapshot renders a blank rather than borrowing another snapshot's
numbers.

---

## 3. What was built

```
ufms-frontend/
  src/components/charts/   PrecisionScale, IndexChart, WardChoropleth,
                           LevelDumbbell, AllocationScatter
  src/components/ui/       the shadcn-idiom primitives, owned here
  src/screens/             the four screens + login
  src/lib/                 api client, auth, useAsync, format
  src/test/                25 tests: screen contracts + encoding
  scripts/                 export-free helpers: visual-check, paper-figures
  public/bbmp-wards.geojson   generated, 198 wards, 661 KB
ufms-backend/
  scripts/export_ward_geojson.py     KML -> GeoJSON, fails on != 198 wards
  docs/figures/                      9 figures + a manifest
```

React 19 + Vite 8 + Tailwind v4 + Recharts + Leaflet, per the stack note.
shadcn components are hand-written into `src/components/ui` rather than pulled
through the CLI — that is what `shadcn init` produces anyway, and it avoids an
interactive installer in a non-interactive environment.

Entry bundle is 282 kB (90 kB gzipped). Recharts and Leaflet are lazy-loaded
behind the three screens that need them, so the landing screen does not pay for
a map it has not been asked for.

### Each screen, and what is load-bearing

**Watchlist.** The scale above. Calls itself a standing watchlist; a test walks
every sentence containing "forecast" or "predict" and requires a negation in the
same sentence.

**Ward index.** 20-quarter series with the `rel = 1.00` reference line, plus a
198-ward choropleth. The map is **diverging**, not sequential — 1.00 is a real
midpoint and a sequential ramp would make an ordinary ward look like a mild
version of a bad one. Classes are multiplicative (×1.41 steps) because the index
is a ratio: linear bins would collapse the entire below-norm arm, since a ratio
cannot go below zero but reaches 8.8. Every point carries `event_days`,
`total_complaints` and the expected count, so a reader can see the ward that
rose because it flooded more and the one that rose because it complained less
about everything else.

**Emerging.** Label rendered as "chronically above norm". A test counts every
occurrence of "accelerating" on the page and requires each to be inside a phrase
that rules it out. `ground_truth_available: false` is a banner, not a footnote.
All five caveats are rendered. The evidence chart is a **dumbbell**, chosen
because it shows both levels rather than emphasising the movement — the movement
is the claim that failed (p = 0.116). Two flagged wards visibly went *down*
between halves, which is the honest picture and exactly why the label is what it
is.

**Allocation.** Two scatter panels side by side, no fitted line anywhere, and no
chart plots spend against the change in index. The `retraction` field is
rendered in full. A test asserts "dose-response", "coefficient", "regression"
and "fitted" appear nowhere outside the retraction block itself.

---

## 4. Where I had to change something you specified

### 4.1 A fifth endpoint

The choropleth needs all 198 wards for one quarter. My first version fired 198
parallel `GET /index/{ward}` calls, which is both slow and wrong: one failure
renders a half-shaded map, and a ward with no colour reads as *"nothing happened
here"* rather than *"no data"* — a different and worse claim.

Added `GET /api/v1/index` (no ward), returning every ward for one quarter with
`available_periods` so the map has a quarter selector. Six tests. The task
specified four endpoints; the fifth is a consequence of the screen you asked
for rather than scope creep, but flagging it as a change.

### 4.2 The basemap is gone

CARTO's tiles now watermark every tile **"API KEY REQUIRED"** — visible across
the whole map in my first screenshot. Rather than swap to another provider I
dropped the tile layer entirely: the 198 wards tile the city, so the polygons
*are* the map, and a road basemap under a diverging choropleth competes with the
encoding it is supposed to support. It also removes a third-party dependency
that can start demanding a key again. Attribution for the boundary source is on
the card.

### 4.3 The token does not survive a refresh

Held in memory only, deliberately — a bearer credential surviving a tab close on
a shared municipal machine is worse than re-typing a password. **The consequence
is that a browser refresh signs you out and deep links do not survive a reload.**
That will look odd in a live demo if you are not expecting it. If you would
rather have `sessionStorage` for the demo, it is a two-line change; I did not
make it unilaterally because it is a security posture, not a preference.

---

## 5. Rendering it and looking at it caught five things the DOM could not

I wrote a script (`npm run visual-check`) that signs in, walks the four screens
at 390 / 768 / 1360 px, and fails on a console error, a failed request, or the
page scrolling sideways. On its first run it found:

1. **The CARTO watermark** (§4.2).
2. **The chance region hidden under its own fill** (§2).
3. **The `rel = 1.00` label sitting on top of the series.** It was positioned
   inside the plot at the top right, which is exactly where Bellandur's line is.
   Moved outside the plot with a reserved right margin.
4. **Long ward names silently clipped.** "Dharmarayaswamy Temple Ward" is 27
   characters, anchored end-aligned, and ran off the left of the SVG viewBox.
   Now truncated with an ellipsis and the full name in a `<title>`.
5. **182 px of horizontal overflow on every screen at 390 px** — the shared
   header. Then 13 px more from a `shrink-0` header-actions block. Both fixed;
   no overflow at any width now.

A sixth came from looking at dark mode: the meter's track was `#184f95`, a
saturated mid-blue, which read as a *third filled segment* rather than as the
empty remainder of the scale. Re-stepped to `#17304f` and split into two tokens
so the dumbbell's second shade did not go dark with it.

None of those six is visible from the DOM, and four of them would have shipped.

---

## 6. Colour, validated rather than chosen

Ran the palette validator before writing any chart code, and again on each
derived ramp:

| Slots | Mode | Result |
|---|---|---|
| `#2a78d6 #eb6834 #1baf7a` | light, all-pairs | PASS (worst CVD ΔE 9.2) |
| `#3987e5 #d95926 #199e70` | dark, all-pairs | PASS (worst CVD ΔE 9.4) |
| cool arm `#86b6ef #2a78d6 #184f95` | light, ordinal | PASS, light end 2.06:1 |
| warm arm `#ec958c #d94a4a #9b302f` | light, ordinal | PASS, light end 2.21:1 |
| cool arm `#184f95 #3987e5 #9ec5f4` | dark, ordinal | PASS, near end 2.15:1 |
| warm arm `#8f2d2a #d04b47 #e8938a` | dark, ordinal | PASS, near end 2.14:1 |

The warm arm is not in the reference palette (only the blue ramp is enumerated),
so I derived it and tuned it until it cleared the same gates the blue arm does —
three candidates failed the light-end contrast floor before `#ec958c` passed.
Everything is a CSS custom property; there is no raw hex in a component.

Light and dark are both defined explicitly, under `prefers-color-scheme` and
under a `data-theme` toggle, so the toggle wins in both directions.

---

## 7. The three doc directives, done

**§1 — `docs/01-evaluation-rules.md` restated on the IFS basis.** The measured
baselines section now leads with **4.79 / 14.08 / 37.72** (136 rain days, 1,289
events), keeps the ERA5 triple **4.72 / 13.55 / 37.36** directly beneath it
labelled as the earlier basis, states that the conclusions are unchanged between
them (36.3% vs 37.3% of ceiling; memory beats weather threefold either way), and
ends with an explicit "never mix them". Three downstream figures that quoted the
ERA5 numbers in passing were updated with them.

**§1 — the profile records that 4.80% was simulated.** §17.4 now says the
quantity has a closed form (`k × events/n`, so per-night precision is `events/n`
independent of k), that the analytic value on the same 136 nights is 4.7868%,
and that 4.79% is what to publish.

**§6 — the profile names the test behind every p-value in the persistence
claim.** §25.1 gains a table: Mann-Whitney U one-sided **0.00014** for flagged
vs other wards, Wilcoxon signed-rank one-sided **0.116** for flagged vs their own
first half. **The 0.23 could not be reconstructed** — it was recorded without
naming its test, so I said so in the profile rather than guess. 0.116 is the
figure the dashboard shows and the one pinned by a test.

**§3 — `CLAUDE.md` records that `interventions` is intentionally empty**, with
the reasoning, so nobody helpfully populates it.

---

## 8. Verification

```
backend    pytest                        143 passed
           alembic check                 clean
frontend   tsc -b                        clean
           vitest run                    25 passed
           vite build                    clean, 282 kB entry (90 kB gzip)
           visual-check 390/768/1360     no console errors, no failed
                                         requests, no horizontal overflow
```

End to end: uvicorn on :8000, dev server proxying `/api`, signed in as a real
officer account, all four screens rendering live data — precision 0.1408 /
oracle 0.3772 / random 0.0479, emerging `chronically_above_norm` with 10 flagged
of 103 eligible and `ground_truth_available: false`, allocation 110 rows with
ρ = +0.474 and the partial −0.050, Jakkur 0.22 → 1.64.

Demo accounts exist in the dev database: `demo.officer@ufms-demo.org` and
`demo.admin@ufms-demo.org`, password `ufms-demo-2026`. **Change or delete them
before anything is deployed** — they are convenience accounts for the demo
machine, not credentials.

---

## 9. What I want a second opinion on

1. **The refresh-signs-you-out trade-off (§4.3).** It is the right security
   posture and it may be the wrong demo behaviour. Your call, and it is small.

2. **Whether the frontend should be in the same repo.** It is a sibling
   directory (`ufms-frontend/`) with its own `package.json`, and the backend's
   `scripts/export_ward_geojson.py` writes into it across that boundary. That is
   fine locally and slightly awkward for a deploy. I did not restructure
   anything; flagging it before Vercel makes it real.

3. **`npm run visual-check` needs Playwright's chromium** (a one-off `npx
   playwright install chromium`). It earned its place today — five real defects
   — but it is a heavier dev dependency than anything else in the project. Keep
   or drop.

4. **Nothing has been deployed.** The revised schedule has 15 Sep as "rehearse on
   the demo machine". Nothing in the build assumes localhost except the dev
   proxy, but the Aiven / Render / Vercel path is untried, and finding out on the
   15th would be bad. If you want it attempted, it should be well before the
   freeze.

5. **The choropleth has no basemap now (§4.2).** I think it reads better and it
   removes a dependency, but it is a visible change from what a reviewer might
   expect a "Leaflet map" to look like. If you want geographic context back,
   plain OSM tiles are a one-line restore.
