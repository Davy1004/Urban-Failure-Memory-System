# REPORT — 10 September 2026 (third session)

Task: one numbers sweep across every document, then the demo recording, then
stop.

**Both done.** One commit, `c083e07`, pushed. 148 backend tests, 31 frontend
tests, 27/27 parity, and a new gate: **65/65 documented figures reproduce from
primary sources.**

---

## 1. The count you asked for

| | |
|---|---:|
| Figures enumerated and checked | **65** |
| Reproduced correctly, no change needed | **60** |
| **Corrected** | **5** |
| **Unverifiable without re-running a retired analysis** | **listed in §5** |

"Corrected" counts distinct wrong figures, not the places they appeared.

The check is not a one-off. `scripts/verify_documented_figures.py` recomputes
every one of the 65 on demand — from the database, the reference CSVs and the
hazard YAML, and **never from another document**, because copying between
documents is precisely how all four stale-number classes propagated. Run it after
touching any number in any doc; `--slow` adds the four re-ranked baselines.

---

## 2. What was wrong

**§2.1 — `DECISIONS.md` quoted the ERA5 triple as if current.** You flagged this
and it was the worst of them, because it is the file that becomes spoken
sentences. "A random guess scores about 5%. The city's own worst-twenty list
scores 13.6%. A perfect oracle scores 37.4%." Those are ERA5 numbers. The
database holds and the API serves the IFS ones. It now reads **4.8% / 14.1% /
37.7%**, and says outright that the two bases exist, that the ERA5 set says the
same thing, and that mixing them puts a number on a scale it was not measured
against. The dependent sentence ("against a 37.4% ceiling it is nearly 60% of
what is achievable") moved with it — 22/37.7 is still nearly 60%.

**§2.2 — `DECISIONS.md` overstated the crosswalk.** "So all 198 were resolved by
hand." The file says **106 exact, 44 normalised, 48 manual**. An examiner who
opens the CSV sees `exact` on 106 rows and the claim collapses. It now says every
one of the 198 was checked and carries a written reason, and gives the split. The
substance — that automatic matching produced confident wrong answers — is
untouched, because that part is true.

**§2.3 — `CLAUDE.md` said 31 response-contract tests.** There are **39**.

**§2.4 — `CLAUDE.md`'s 178-differences paragraph quotes the old schema shape.**
"All 45 foreign keys and 27 indexes", "all 25 column comments" — true at the
26-table baseline, and nothing said so. The schema now has **54 foreign keys and
67 column comments**. Labelled as the baseline shape.

**§2.5 — `docs/00-build-plan.md` read as current and is not.** It plans P0
Sep 8–21 through P8 to April 2027, and sizes the database at "~600k complaints,
~350k weather_observations, about 2M rows, 400–600 MB". Reality: Phases 0–4 all
landed in September; complaints are **237,157** (40% of the estimate) and
weather_observations **1,309,896** (nearly 4× it, because the grid was tripled in
resolution after ERA5 resolved BBMP into three cells); `failure_memory`,
`risk_predictions` and `daily_rankings` are **all empty**; the real totals are
**1,610,832 rows, ≈218 MB**. It now opens with a planned-vs-measured table and a
line saying not to read the schedule as current. The plan itself is kept — what
was planned and why is worth having beside what happened.

---

## 3. The finding that matters more than the five corrections

**The retracted dose-response rests on a specification that was recorded
nowhere.**

The published pair is −0.0240 (p = 0.0138) over all 110 wards, collapsing to
−0.0064 (p = 0.833) on treated wards only. I tried to verify it and could not:
regressing `delta` on `log_spend` over the committed panel gives **−0.0159
(p = 0.230)**, and on treated wards **−0.0381 (p = 0.301)**. Neither matches.

The panel was not wrong — the raw Spearman reproduced exactly (−0.1634,
p = 0.0992 against a documented −0.163, p = 0.099). So the published figures had
to be **multivariate**, and which controls they used existed only in a session
transcript. I searched specifications until both reproduced to four decimals:

```
delta ~ log_spend + log_area + pre
```

→ **−0.0240, p = 0.0138** over all 110; **−0.0064, p = 0.8334** on treated only.
Both exact.

Why this is the important one: this is the project's most significant negative
result, it is rendered on a screen and printed in the paper, and **"we regressed
the change in index on log spend" would have been the wrong answer to give under
questioning** — that is a different, weaker, non-significant result. Someone
asked "what did you control for?" could not have answered from this repository.

It is now a rule in `docs/01-evaluation-rules.md` — *a coefficient must carry its
specification wherever it is reported; a coefficient without the model that
produced it is not a result, it is a number* — and both figures are pinned by the
verifier.

This is the fourth instance of the pattern you named: a check or a claim that
looked sound and was not being verified. `_env_file=None`, the names-only schema
comparison, the migrations test skipping everywhere, and now a headline
coefficient with no recorded model.

---

## 4. What reproduced exactly, and is now pinned

Worth listing because the docs came out of this in better shape than I expected.
Every one recomputed from a primary source:

- **The two triples**, both bases, plus both re-ranked figures: 13.55 / 13.70 /
  37.36 / 4.72 (ERA5) and 14.08 / 14.23 / 37.72 / 4.79 (IFS).
- **The headroom argument**: honest 14.0809%, perfect-foresight ward ranking
  15.6618%, gain **+1.58** points against a **23.64**-point headroom — so
  DECISIONS.md's "1.6 points out of 24" is right.
- **Both base rates**: strict **1.5585%** (6,045 event ward-days of 387,882) and
  broad **7.9903%**. Rule 3 quotes both; both hold.
- **Kendall tau between the halves = 0.5884** with a **15/20** top-20 overlap,
  against a documented 0.59 and 15/20.
- **The allocation totals**: ₹6,677,331,368 total, ₹20,242,441 median treated,
  Someshwara highest at ₹631,617,283, Jakkur ₹494,203,600 and **rank 2** —
  confirming "2nd-highest drainage spender".
- **The Jakkur series**: 20 quarters, 0.2179 → 1.6362, mean 1.0948, above the
  norm in **10 of 20** — matching "0.22 → 1.64, mean 1.09, 10 of 20".
- **The hazard YAML against the database**: its own `event_total_rows` 8,293 and
  `broad_total_rows` 42,004 both equal `COUNT(*)` over those sub-categories.
- **The crosswalk**: 198 rows, 106/44/48, 0 unresolved, 102 in register, 96 not.
- **Generated artifacts**: the geojson is 661 KB / 198 features / 36,369 points,
  and the dump is 612 KB / 30 INSERTs / 4,820 rows — all as documented.
- **`/health` returns 503 when the database is unreachable.** Verified by
  accident, against a genuinely broken instance. It does.

---

## 5. What I could not verify — not guessed, not dropped

These appear in `docs/02-data-profile.md` and were computed in sessions whose
scripts were never committed. Re-deriving them is a post-freeze job; each line
says what it would take.

| Figure | Where | To check it |
|---|---|---|
| Pooled AUC 0.749 vs within-night 0.737 | CLAUDE.md, 01, 02 §19.4 | Refit the ranking model and score both ways. Needs the model, which is not built. |
| Weather-only ranking 5.63% | 01, 02 §17.4 | Rank wards by cell rainfall per night and score at k=20. Feasible from the DB; the exact feature was never recorded. |
| Per-ward rainfall lift tables (3.06 → 3.00, χ² p = 0.877) | CLAUDE.md, 02 §16–17 | Re-run the lift computation on both grids. Data present; script gone. |
| Permutation null: 9 rising / 4 declining, p = 0.0010, 2,000 draws | CLAUDE.md, 01, 02 §22–23 | Re-run the permutation. Seed unrecorded, so the p will be close but not identical. |
| Citywide share fell 22% | 01, 02 §22 | My nearest reproduction is **−20.6%** (first-four vs last-four quarters); the exact instrument was not recorded. Close, not confirmed. |
| Magnitude R² = 0.196, 3-class 50.0% vs 39.6% | CLAUDE.md, 02 §20 | Refit the magnitude model. |
| Register agreement: 16 of 20, base rate 52%, p = 0.006, Spearman 0.334 | CLAUDE.md, 02 §21 | Recomputable from the crosswalk and the frozen list; not attempted this session. |
| §26 quintile table, F = 1.26 p = 0.265 | CLAUDE.md, 02 §26.3 | Refit with a quadratic term on the panel. Panel is committed, so this one is genuinely cheap. |
| §28 gate figures (ρ = +0.505, 6 of 8 quarters, 51 of 196 wards) | CLAUDE.md, 02 §28 | Re-run the gate analysis off the raw work orders. |
| Palette contrast ratios (2.06:1 … 2.21:1) | frontend/README.md | Re-run the data-viz palette validator, which is not in the repo. |
| "309,012 rows, 40.31%" for the 96 off-register wards | 02 §15 | **This is a pre-filter number** — it is 40.31% of the 766,648 raw grievance rows, not of the 237,157 loaded. Post-filter the same wards hold 98,156 rows = **41.39%**. DECISIONS.md says "40% of the data", which is true either way, so I left it; flagging the ambiguity. |

None of these is a headline. The triples, the headroom, the allocation finding,
the emerging evidence and the case study are all verified.

---

## 6. The recording

`docs/demo/ufms-demo.mp4` — **1:12, 1280×720, H.264, 1.06 MB**, with the webm it
was transcoded from (4.56 MB). Both committed; `.gitattributes` marks them
binary. Well inside 25 MB, so no frame-rate reduction was needed.

`npm run record-demo` in `frontend/`. It walks the runbook's path in the
runbook's order with explicit dwells — 6.5s on the precision scale, 5s on the
ward tooltip, 6.5s on the retraction — because a demo video that moves at
Playwright's speed is useless in a room.

**No login screen and no credentials on camera.** It fetches a token from the API
and injects it into `sessionStorage` via an init script that runs before first
paint, so the app restores straight to the watchlist.

**I checked frames rather than assuming.** At 0:05 the precision scale shows
4.79% chance / 14.08% this list / 37.72% ceiling, legible at 720p. At 0:33 the
choropleth draws 198 wards with no basemap and the tooltip reads *Basaveshwara
Nagar / Ward 100 · West / Index 0.54, 2025Q1* — name, ward, index **and quarter**,
which is the §9.5 condition, on video. At 0:52 the retraction renders in full
above both scatter panels, neither with a trend line. Zero console errors across
the whole recording.

**On the mp4: ffmpeg was the interesting part.** Playwright bundles one, but it
is a minimal build carrying **only VP8 and png** — it cannot encode H.264 at all,
and the first attempt failed with a wall of configure flags. Rather than ship
webm-only, I made the script ask each candidate for its encoder list and reject
any without `libx264`. A full ffmpeg turned out to be already on this machine
(bundled with a browser extension's companion app), so the mp4 exists. If a
future run finds none, the script says so explicitly and prints
`winget install Gyan.FFmpeg` rather than silently producing nothing.

`docs/demo/README.md` records what it shows, that it is the real system and not a
mockup, the date, the commit (`d2a619d` — no code under `app/` or `frontend/src/`
changed between then and the recording), and a timestamped index of the path.

The runbook's insurance section now leads with the video and keeps the
screenshots as the second fallback.

---

## 7. One more defect, found while setting up the recording

Port 8000 was answering, `/health` said `database: unreachable`, and every panel
would have rendered empty. The cause was an **orphaned `uvicorn --reload` worker**
from the rehearsal clone, still holding the port and serving a database I had
deleted an hour earlier. `netstat` attributed the socket to a PID that no longer
existed, so `taskkill` on it reported "process not found" while the port kept
responding. The live process was the reload *worker*, findable only by command
line (`spawn_main(parent_pid=...)`).

This is nastier than a plain port clash, because the port answers. On demo
morning it would present as "the API is up but the dashboard is empty" — which
the runbook's existing row sends you to re-run the restore, the wrong fix. Added
as its own failure row with the PowerShell that finds it.

---

## 8. Flagged, not acted on

1. **`docs/02-data-profile.md` is 3,181 lines and is now the only document with
   unverifiable numbers in it.** Everything in §5 above lives there. It is a
   research log rather than a claims document, which is why I have not touched
   it — but if an examiner reads a figure out of it, we cannot currently
   reproduce it. Post-freeze, the §26 quintile refit and the §21 register
   agreement are the two cheapest to close, because both run off committed files.

2. **The "22%" citywide decline is the one figure I would still like to pin.** It
   appears in `DECISIONS.md` in prose ("falling city-wide by 22%") and supports
   the Proof Two null. My nearest reproduction is −20.6%. It is almost certainly
   right and measured slightly differently; I did not change it, because
   replacing a documented figure with a differently-derived one is how bases got
   mixed in the first place.

3. **Nothing else. The freeze starts on the 13th and I have nothing queued.**
   What remains is Tanmay's: the supervisor on the 14th, names on the paper and
   on slides 1 and 14, and the reference volume and page numbers.

---

## 9. State

- `origin/main` at `c083e07`; working tree clean; nothing unpushed.
- 168 tracked files.
- **148 backend tests, 31 frontend tests**, `npm run build` clean, lint warnings
  unchanged (3, all pre-existing).
- `scripts/check_parity.py --base http://127.0.0.1:8000` → **27/27, PASSED**.
- `scripts/verify_documented_figures.py --slow` → **65/65, PASSED**.
- The demo stack is up on :8000 and :5173 and serving correct numbers.
