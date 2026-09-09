# The demo recording

**`ufms-demo.mp4`** — 1:12, 1280×720, H.264. Play this one.
**`ufms-demo.webm`** — the same recording, as produced. Kept because it is the
original; the mp4 is transcoded from it.

Recorded **10 September 2026**, against the application code at commit
**`d2a619d`** — the recording was made before this file was committed, and no
code under `app/` or `frontend/src/` changed in between.

## What it is

**A recording of the real system, not a mockup.** Every number on screen was
served by the live API against the loaded database at the moment of recording:
precision@20 of 14.08% with its 4.79% chance floor and 37.72% oracle ceiling, the
frozen top-20 headed by Bellandur, all 198 ward polygons, the emerging screen's
`ground_truth_available: false` banner, and the allocation retraction in full.
Nothing is redrawn, staged or re-typed.

It follows `../03-demo-runbook.md`'s five-minute path, in that order:

| | Screen | What to look at |
|---|---|---|
| 0:00 | **Watchlist** | The precision scale. The mark sits at 14.08% on a track that runs from a 4.79% chance floor to a 37.72% ceiling — the whole point is that the number is unreadable without the other two. |
| 0:12 | Watchlist | The twenty wards, ranked, with what actually happened on the held-out rain days. |
| 0:21 | **Ward index** | One ward's relative index against the 1.00 city norm, then the choropleth: 198 wards, diverging about 1.00, **no basemap**. |
| 0:33 | Ward index | A ward tooltip — name, ward number, zone, index **and quarter**. With no basemap the tooltip is the only thing identifying a polygon. |
| 0:38 | **Emerging** | The label is *chronically above norm*, and the banner says the flags cannot be validated against BBMP's own additions because the register carries no listing years. |
| 0:48 | **Allocation** | The retraction, rendered in full, before the charts. Then both scatter panels — spend against ward area, spend against flooding need — with **no trend line on either**, because the dose-response is retracted. |

## Why it exists

The demo runs from the project laptop and `03-demo-runbook.md` covers every way
the *software* can fail. It covers none of the ways the *room* can fail: a flat
battery, a missing HDMI adapter, a projector that will not sync, being asked to
present from the podium machine, Docker declining to start on the morning.

This is the fallback for all of those at once. It is not a substitute for the
live demo — run the live one whenever it is possible.

## Regenerating it

```bash
uvicorn app.main:app                    # terminal 1, :8000
cd frontend && npm run dev              # terminal 2, :5173
cd frontend && npm run record-demo      # terminal 3
```

The recording starts **already signed in** — the token is fetched from the API
and injected into `sessionStorage` before the first paint, so the login screen
and the demo password never appear on camera. That matters for a file that may
end up emailed or on a slide.

**The mp4 needs an H.264 encoder.** Playwright bundles an ffmpeg, but it is a
minimal build carrying only VP8 and cannot produce one — the script checks each
candidate's encoder list and refuses to use one without `libx264`, rather than
writing a file nothing plays. If it reports that none was found:

```bash
winget install Gyan.FFmpeg
npm run record-demo
```

A browser will play the webm on any modern machine; PowerPoint will not embed it.
That is the reason the mp4 is the one to rely on.
