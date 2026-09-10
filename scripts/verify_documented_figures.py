"""Recompute every documented figure from a primary source, and fail on drift.

    python scripts/verify_documented_figures.py
    python scripts/verify_documented_figures.py --slow    # includes the re-rank

Why this exists
---------------
Four separate classes of stale number were caught during September 2026, every
one of them incidentally while doing something else:

* "31 tables" against an actual 32;
* `information_schema.TABLE_ROWS` **estimates** quoted as if they were
  `COUNT(*)` — 1,175,475 for a table holding 1,309,896 rows;
* 13.70% quoted on the ERA5 basis inside an otherwise-IFS table;
* "143 backend tests" after the suite had grown to 148.

Six days before an evaluation, every one of those numbers gets read aloud. So
this is the pass that goes looking rather than waiting to trip over the next one.

**Each check recomputes its figure from the database, a reference CSV or the
hazard YAML — never from another document.** That is the rule the failures above
violated: a wrong number propagates by being copied, so a check that compares two
documents confirms the copy rather than the fact.

What this does NOT cover
------------------------
Figures that would need a retired analysis re-run — the pooled-AUC comparison,
the weather-only ranking, the per-ward rainfall lift tables, the permutation
null, the magnitude model, and the section 28 gate figures. Those were computed
in sessions whose scripts were never committed. They are listed as unverifiable
in `REPORT.md` rather than silently trusted, and re-deriving them is a
post-freeze job.

Three that *were* on that list are now covered: the section 21 register
agreement (the paper's external check), the section 26.3 quintile table with its
confidence intervals and quadratic F-test, and the citywide share decline with
the instrument that produces it.

`scripts/check_parity.py` covers the 27 figures the API serves. This covers the
ones that live in the database and the reference files behind it. Between them
every headline number in the docs is reproducible on demand.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Callable

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Every check: a label, where the figure is written down, the expected value,
# an absolute tolerance (0 = exact), and how to recompute it.
Check = tuple[str, str, Any, float, Callable[[Any], Any]]


def _scalar(sql: str, **kw) -> Callable[[Any], Any]:
    return lambda db: db.execute(text(sql), kw).scalar()


def _count(table: str) -> Callable[[Any], Any]:
    """COUNT(*), deliberately - never information_schema.TABLE_ROWS, which is an
    estimate for InnoDB and was the source of two published wrong numbers."""
    return _scalar(f"SELECT COUNT(*) FROM `{table}`")


def _crosswalk(col: str, value: Any = None) -> Callable[[Any], Any]:
    def go(_db):
        cw = pd.read_csv(ROOT / "data/reference/ward_crosswalk.csv")
        if value is None:
            return len(cw) if col == "__rows__" else int(cw[col].sum())
        return int((cw[col] == value).sum())
    return go


def _yaml_rows(kind: str) -> Callable[[Any], Any]:
    def go(_db):
        y = yaml.safe_load((ROOT / "data/reference/hazard_categories.yaml").read_text(
            encoding="utf-8"))
        w = y["waterlog"]
        if kind == "event":
            return sum(e["rows"] for e in w["event"])
        if kind == "maintenance":
            return sum(e["rows"] for e in w["maintenance"])
        return w[kind]
    return go


def _db_rows_for(kind: str) -> Callable[[Any], Any]:
    """Rows in `complaints` matching the YAML's strict or broad sub-categories."""
    def go(db):
        y = yaml.safe_load((ROOT / "data/reference/hazard_categories.yaml").read_text(
            encoding="utf-8"))
        w = y["waterlog"]
        subs = [e["sub_category"] for e in w["event"]]
        if kind == "broad":
            subs += [e["sub_category"] for e in w["maintenance"]]
        ph = ", ".join(f":s{i}" for i in range(len(subs)))
        return db.execute(
            text(f"SELECT COUNT(*) FROM complaints WHERE sub_category IN ({ph})"),
            {f"s{i}": s for i, s in enumerate(subs)},
        ).scalar()
    return go


def _alloc(fn: str) -> Callable[[Any], Any]:
    def go(db):
        al = pd.DataFrame(db.execute(text(
            "SELECT l.area_name w, a.drainage_spend s, a.is_treated t "
            "FROM ward_allocation a JOIN locations l ON l.location_id=a.location_id"
        )).all(), columns=["w", "s", "t"])
        al["s"] = al["s"].astype(float)
        if fn == "total":
            return al["s"].sum()
        if fn == "median_treated":
            return al[al["t"] == 1]["s"].median()
        if fn == "max":
            return al["s"].max()
        if fn == "max_ward":
            return al.loc[al["s"].idxmax(), "w"]
        if fn == "jakkur":
            return float(al[al["w"] == "Jakkur"]["s"].iloc[0])
        if fn == "jakkur_rank":
            j = float(al[al["w"] == "Jakkur"]["s"].iloc[0])
            return int((al["s"] > j).sum()) + 1
        raise KeyError(fn)
    return go


def _jakkur_index(fn: str) -> Callable[[Any], Any]:
    def go(db):
        rows = db.execute(text(
            "SELECT q.rel_index FROM ward_quarter_index q "
            "JOIN locations l ON l.location_id=q.location_id "
            "WHERE l.area_name='Jakkur' AND q.period_type='quarter' "
            "ORDER BY q.period_start")).scalars().all()
        v = [float(x) for x in rows]
        return {"first": v[0], "last": v[-1], "mean": sum(v) / len(v),
                "n": len(v), "above": sum(1 for x in v if x > 1.0)}[fn]
    return go


def _dose(fn: str) -> Callable[[Any], Any]:
    """The retracted dose-response, at the specification that produced it.

    **The specification is the point of this check.** The published pair -
    -0.0240 (p = 0.0138) over all 110 wards, collapsing to -0.0064 (p = 0.833)
    on treated wards only - is a *multivariate* coefficient, and which controls
    it used was never written down anywhere in this repository. It was recovered
    on 10 Sep 2026 by searching specifications against
    `ward_dose_response_panel.csv` until both figures reproduced to four
    decimals, and it is:

        delta ~ log_spend + log_area + pre

    The bivariate version is a different and weaker result (-0.0159, p = 0.230),
    so "we regressed the change in index on log spend" would have been the wrong
    answer to give under questioning. Pinned here so the retraction - the
    project's most important negative result - stays reproducible.
    """
    def go(_db):
        import numpy as np
        from scipy import stats

        d = pd.read_csv(ROOT / "data/reference/ward_dose_response_panel.csv")
        frame = d if fn.startswith("all") else d[d["spend"] > 0]
        xs = ["log_spend", "log_area", "pre"]
        X = np.column_stack([np.ones(len(frame))]
                            + [frame[x].to_numpy() for x in xs])
        y = frame["delta"].to_numpy()
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        dof = X.shape[0] - X.shape[1]
        cov = (resid @ resid / dof) * np.linalg.pinv(X.T @ X)
        se = np.sqrt(np.diag(cov))
        t = beta[1] / se[1]
        pval = 2 * (1 - stats.t.cdf(abs(t), dof))
        return beta[1] if fn.endswith("beta") else pval
    return go


def _broad_base_rate(db) -> float:
    """The 7.99% broad-label ward-day base rate, beside the 1.56% strict one.

    Both matter: engineering rule 3 quotes them together, because "no failure"
    scores 98.4% against the strict label and 92% against the broad one, and a
    reader who sees only one of them cannot tell how much the label choice moves.
    """
    import yaml as _yaml
    from app.derived import WATCHLIST_TEST_END, WATCHLIST_TRAIN_START
    from app.derived.watchlist import _ward_count
    from app.ingestion.base import resolve_city

    w = _yaml.safe_load((ROOT / "data/reference/hazard_categories.yaml").read_text(
        encoding="utf-8"))["waterlog"]
    subs = [e["sub_category"] for e in w["event"]] + \
           [e["sub_category"] for e in w["maintenance"]]
    ph = ", ".join(f":s{i}" for i in range(len(subs)))
    city = resolve_city(db, "Bengaluru")
    n = db.execute(text(
        f"SELECT COUNT(*) FROM (SELECT c.location_id, DATE(c.reported_at) d "
        f"FROM complaints c JOIN locations l ON l.location_id=c.location_id "
        f"WHERE l.geom_level='ward' AND c.sub_category IN ({ph}) "
        f"AND DATE(c.reported_at) BETWEEN :a AND :b "
        f"GROUP BY c.location_id, DATE(c.reported_at)) t"),
        {**{f"s{i}": v for i, v in enumerate(subs)},
         "a": WATCHLIST_TRAIN_START, "b": WATCHLIST_TEST_END}).scalar()
    days = (WATCHLIST_TEST_END - WATCHLIST_TRAIN_START).days + 1
    return n / (days * _ward_count(db, city.city_id)) * 100


def _geojson(fn: str) -> Callable[[Any], Any]:
    """The committed ward polygons. Their size and point count are quoted in three
    places, and the file is generated - so a regeneration that changed either
    would leave the docs wrong with nothing to notice it."""
    def go(_db):
        import json
        f = ROOT / "frontend/public/bbmp-wards.geojson"
        if fn == "kb":
            return round(f.stat().st_size / 1024)
        d = json.loads(f.read_text(encoding="utf-8"))
        if fn == "features":
            return len(d["features"])
        return sum(
            len(r) for feat in d["features"]
            for poly in ([feat["geometry"]["coordinates"]]
                         if feat["geometry"]["type"] == "Polygon"
                         else feat["geometry"]["coordinates"])
            for r in poly)
    return go


def _register(fn: str) -> Callable[[Any], Any]:
    """Profile section 21: does the complaint ranking agree with BBMP's own register?

    This is the paper's independent external check and the strongest evidence in
    it - two unrelated instruments converging - so it is worth being able to
    reproduce on demand. Everything here comes from `ward_crosswalk.csv` and the
    frozen watchlist, both committed, over the TRAIN window (the frozen list's own
    window). Scored on the full window every figure moves, which is the sort of
    basis slip the evaluation rules exist to prevent.
    """
    def go(db):
        from scipy import stats

        from app.derived import WATCHLIST_AS_OF, WATCHLIST_TRAIN_START
        from app.derived.watchlist import _event_days
        from app.ingestion.base import resolve_city

        city = resolve_city(db, "Bengaluru")
        cid = city.city_id
        cw = pd.read_csv(ROOT / "data/reference/ward_crosswalk.csv")
        on_reg = dict(zip(cw["bbmp_ward_no"].astype(int).astype(str),
                          cw["in_flood_register"].astype(bool)))

        w = pd.DataFrame(db.execute(text(
            "SELECT location_id, ward_no, area_name FROM locations "
            "WHERE city_id=:c AND geom_level='ward'"), {"c": cid}).all(),
            columns=["location_id", "ward_no", "ward"])
        w["ward_no"] = w["ward_no"].astype(str).str.strip()
        w["on_reg"] = w["ward_no"].map(on_reg)

        pts = pd.DataFrame(db.execute(text(
            "SELECT ward_no, COUNT(*) n FROM locations WHERE geom_level<>'ward' "
            "AND is_known_hotspot=1 AND ward_no IS NOT NULL GROUP BY ward_no")).all(),
            columns=["ward_no", "pts"])
        pts["ward_no"] = pts["ward_no"].astype(str).str.strip()
        w = w.merge(pts, on="ward_no", how="left")
        w["pts"] = w["pts"].fillna(0).astype(int)

        ev = _event_days(db, cid, WATCHLIST_TRAIN_START, WATCHLIST_AS_OF)
        w = w.merge(ev.groupby("location_id").size().rename("events"),
                    left_on="location_id", right_index=True, how="left")
        w["events"] = w["events"].fillna(0).astype(int)

        top = [r.ward for r in db.execute(text(
            "SELECT l.area_name ward FROM watchlist_entries e "
            "JOIN locations l ON l.location_id=e.location_id "
            "ORDER BY e.rank_position")).all()]
        t20 = w[w["ward"].isin(top)]
        hits = int(t20["on_reg"].sum())
        n, kk, k = len(w), int(w["on_reg"].sum()), 20
        r, nr = w[w["on_reg"]], w[~w["on_reg"]]

        if fn == "hits":
            return hits
        if fn == "expected":
            return k * kk / n
        if fn == "p_hyper":
            return float(stats.hypergeom.sf(hits - 1, n, kk, k))
        if fn == "coverage_pct":
            return kk / n * 100
        if fn == "mean_reg":
            return r["events"].mean()
        if fn == "mean_nonreg":
            return nr["events"].mean()
        if fn == "spearman":
            return float(stats.spearmanr(w["events"], w["pts"])[0])
        if fn == "kendall":
            return float(stats.kendalltau(w["events"], w["pts"])[0])
        if fn == "mw_p":
            return float(stats.mannwhitneyu(r["events"], nr["events"],
                                            alternative="greater").pvalue)
        if fn == "off_register":
            return ", ".join(sorted(t20[~t20["on_reg"]]["ward"]))
        raise KeyError(fn)
    return go


def _panel_ols(xs: list[str], term: str, want: str):
    """OLS on the committed dose-response panel, returning one term's beta or p."""
    def go(_db):
        import numpy as np
        from scipy import stats

        d = pd.read_csv(ROOT / "data/reference/ward_dose_response_panel.csv")
        d = d.assign(log_spend_sq=d["log_spend"] ** 2)
        X = np.column_stack([np.ones(len(d))] + [d[x].to_numpy() for x in xs])
        y = d["delta"].to_numpy()
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        dof = X.shape[0] - X.shape[1]
        cov = (resid @ resid / dof) * np.linalg.pinv(X.T @ X)
        se = np.sqrt(np.diag(cov))
        i = xs.index(term) + 1
        if want == "beta":
            return beta[i]
        if want == "r2":
            tss = ((y - y.mean()) ** 2).sum()
            return 1 - (resid @ resid) / tss
        t = beta[i] / se[i]
        return 2 * (1 - stats.t.cdf(abs(t), dof))
    return go


def _quintile(q: str, fn: str) -> Callable[[Any], Any]:
    """Profile section 26.3. DECISIONS.md says this table must never be published
    without its confidence intervals, because only Q1 is distinguishable from
    zero - so the CIs are checked here, not just the means."""
    def go(_db):
        from scipy import stats

        d = pd.read_csv(ROOT / "data/reference/ward_dose_response_panel.csv")
        tr = d[d["spend"] > 0].copy()
        tr["q"] = pd.qcut(tr["spend"], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
        g = (d[d["spend"] <= 0] if q == "Untreated" else tr[tr["q"] == q])["delta"]
        if fn == "n":
            return len(g)
        if fn == "mean":
            return g.mean()
        if fn == "p":
            return float(stats.ttest_1samp(g, 0).pvalue)
        lo, hi = stats.t.interval(0.95, len(g) - 1, loc=g.mean(), scale=stats.sem(g))
        return lo if fn == "ci_lo" else hi
    return go


def _quadratic_f(_db) -> float:
    """The F-test for the added quadratic term: 1.26, p = 0.265. This is the
    figure that says the apparent non-monotonicity in the quintile table is not
    real, so it carries the 'do not claim a U-shape' rule."""
    import numpy as np

    d = pd.read_csv(ROOT / "data/reference/ward_dose_response_panel.csv")
    d = d.assign(log_spend_sq=d["log_spend"] ** 2)
    y = d["delta"].to_numpy()

    def rss(xs):
        X = np.column_stack([np.ones(len(d))] + [d[x].to_numpy() for x in xs])
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        r = y - X @ b
        return r @ r, X.shape[0] - X.shape[1]

    r0, _ = rss(["log_spend", "log_area", "pre"])
    r1, dof1 = rss(["log_spend", "log_spend_sq", "log_area", "pre"])
    return ((r0 - r1) / 1) / (r1 / dof1)


def _city_decline(_db) -> float:
    """The citywide event-share decline over the window, as a percentage.

    **The instrument is the point.** The documented "22%" is the POOLED first-four
    against last-four quarters - total events over total complaints in each block,
    which is the construction `ward_relative_trends.csv` was built around
    (`ev_first4`, `co_first4`, ...). Taking the mean of the per-quarter shares
    instead gives -20.6%, and endpoint or fitted-trend instruments give anything
    from -35% to -59%. The figure is load-bearing: it is why Proof Two must be
    benchmarked to the city trend rather than to zero, and testing against zero
    gave a false 0-rising. So the estimator travels with it.
    """
    t = pd.read_csv(ROOT / "data/reference/ward_relative_trends.csv")
    first = t["ev_first4"].sum() / t["co_first4"].sum()
    last = t["ev_last4"].sum() / t["co_last4"].sum()
    return (last / first - 1) * 100


def _base_rate(_db) -> Any:
    from datetime import date

    from app.derived import WATCHLIST_TEST_END, WATCHLIST_TRAIN_START
    from app.derived.watchlist import _event_days, _ward_count
    from app.ingestion.base import resolve_city

    db = _db
    city = resolve_city(db, "Bengaluru")
    n_wards = _ward_count(db, city.city_id)
    ev = _event_days(db, city.city_id, WATCHLIST_TRAIN_START, WATCHLIST_TEST_END)
    days = (WATCHLIST_TEST_END - WATCHLIST_TRAIN_START).days + 1
    assert isinstance(WATCHLIST_TRAIN_START, date)
    return len(ev) / (days * n_wards) * 100


def _headroom(fn: str) -> Callable[[Any], Any]:
    def go(db):
        from app.derived import (
            RAIN_THRESHOLD_MM, WATCHLIST_AS_OF, WATCHLIST_K, WATCHLIST_TEST_END,
            WATCHLIST_TEST_START, WATCHLIST_TRAIN_START,
        )
        from app.derived.watchlist import (
            _event_days, _ward_count, rain_days, score_watchlist,
        )
        from app.ingestion.base import resolve_city

        city = resolve_city(db, "Bengaluru")
        cid = city.city_id
        names = dict(db.execute(text(
            "SELECT location_id, area_name FROM locations WHERE city_id=:c"),
            {"c": cid}).all())
        n_wards = _ward_count(db, cid)
        days = rain_days(db, cid, WATCHLIST_TEST_START, WATCHLIST_TEST_END,
                         RAIN_THRESHOLD_MM, "ecmwf_ifs")
        ev = _event_days(db, cid, WATCHLIST_TEST_START, WATCHLIST_TEST_END)
        ev = ev[ev["d"].isin(set(days))]

        def top(frame):
            c = frame.groupby("location_id").size().rename("n").reset_index()
            c["a"] = c["location_id"].map(names)
            return c.sort_values(["n", "a"], ascending=[False, True]) \
                    .head(WATCHLIST_K)["location_id"].tolist()

        train = _event_days(db, cid, WATCHLIST_TRAIN_START, WATCHLIST_AS_OF)
        honest = score_watchlist(top(train), ev, days, n_wards, WATCHLIST_K)
        # "Perfect foresight": one fixed list chosen with the test period's own
        # answers. It is an upper bound on any WARD-LEVEL score, which is the
        # quantity the headroom claim is about.
        fore = score_watchlist(top(ev), ev, days, n_wards, WATCHLIST_K)
        return {
            "honest": honest["precision_at_k"] * 100,
            "foresight": fore["precision_at_k"] * 100,
            "gain": (fore["precision_at_k"] - honest["precision_at_k"]) * 100,
            "headroom": (honest["oracle_at_k"] - honest["precision_at_k"]) * 100,
        }[fn]
    return go


CHECKS: list[Check] = [
    # ---- schema shape -----------------------------------------------------
    ("base tables (excl alembic_version)", "CLAUDE.md, README.md, 03, 04", 32, 0,
     _scalar("SELECT COUNT(*) FROM information_schema.TABLES "
             "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_TYPE='BASE TABLE' "
             "AND TABLE_NAME<>'alembic_version'")),
    ("views", "CLAUDE.md, 03, 04", 3, 0,
     _scalar("SELECT COUNT(*) FROM information_schema.TABLES "
             "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_TYPE='VIEW'")),
    ("SQLAlchemy models == tables", "CLAUDE.md, README.md", 32, 0,
     lambda db: len(__import__("app.db.base", fromlist=["Base"]).Base.metadata.tables)),

    # ---- row counts, by COUNT(*) -----------------------------------------
    ("weather_observations rows", "04, export_demo_dump.py, REPORT.md", 1_309_896, 0,
     _count("weather_observations")),
    ("complaints rows", "CLAUDE.md, 02, 04", 237_157, 0, _count("complaints")),
    ("weather_daily cell-days", "02 sec 17.3", 54_579, 0, _count("weather_daily")),
    ("weather_cells", "CLAUDE.md", 23, 0, _count("weather_cells")),
    ("locations", "CLAUDE.md", 596, 0, _count("locations")),
    ("ward_quarter_index rows", "CLAUDE.md, 01", 3_960, 0, _count("ward_quarter_index")),
    ("ward_period_totals rows", "CLAUDE.md", 4_356, 0, _count("ward_period_totals")),
    ("emerging_watch rows", "CLAUDE.md, 01", 103, 0, _count("emerging_watch")),
    ("ward_allocation rows", "CLAUDE.md", 110, 0, _count("ward_allocation")),
    ("watchlist_entries rows", "CLAUDE.md", 20, 0, _count("watchlist_entries")),
    ("interventions is EMPTY (deliberately)", "CLAUDE.md, 03", 0, 0,
     _count("interventions")),

    # ---- locations breakdown --------------------------------------------
    ("ward rows in locations", "CLAUDE.md, 02", 198, 0,
     _scalar("SELECT COUNT(*) FROM locations WHERE geom_level='ward'")),
    ("register points in locations", "CLAUDE.md, 02", 398, 0,
     _scalar("SELECT COUNT(*) FROM locations WHERE geom_level<>'ward'")),
    ("is_known_hotspot on ward rows (must be 0)", "CLAUDE.md, DECISIONS.md", 0, 0,
     _scalar("SELECT COALESCE(SUM(is_known_hotspot),0) FROM locations "
             "WHERE geom_level='ward'")),
    ("register points carrying a ward_no", "DECISIONS.md, CLAUDE.md", 200, 0,
     _scalar("SELECT COUNT(*) FROM locations "
             "WHERE geom_level<>'ward' AND ward_no IS NOT NULL")),
    ("first_listed_year populated (must be 0)", "CLAUDE.md, DECISIONS.md", 0, 0,
     _scalar("SELECT COUNT(*) FROM locations WHERE first_listed_year IS NOT NULL")),
    ("locations with a cell_id", "CLAUDE.md", 596, 0,
     _scalar("SELECT COUNT(*) FROM locations WHERE cell_id IS NOT NULL")),

    # ---- ward crosswalk --------------------------------------------------
    ("crosswalk rows", "02 sec 15, sec 16", 198, 0, _crosswalk("__rows__")),
    ("crosswalk exact", "02 sec 16.1", 106, 0, _crosswalk("match_method", "exact")),
    ("crosswalk normalised", "02 sec 16.1", 44, 0, _crosswalk("match_method", "normalised")),
    ("crosswalk manual", "02 sec 16.1", 48, 0, _crosswalk("match_method", "manual")),
    ("crosswalk unresolved (must be 0)", "02 sec 16.1", 0, 0,
     _crosswalk("match_method", "unresolved")),
    ("crosswalk in_flood_register", "DECISIONS.md, 02", 102, 0,
     _crosswalk("in_flood_register")),

    # ---- the hazard YAML, against the database --------------------------
    ("YAML event_total_rows == its own parts", "hazard_categories.yaml", 8_293, 0,
     _yaml_rows("event")),
    ("YAML maintenance_total_rows == its parts", "hazard_categories.yaml", 33_711, 0,
     _yaml_rows("maintenance")),
    ("YAML broad_total_rows == event+maintenance", "hazard_categories.yaml", 42_004, 0,
     lambda db: _yaml_rows("event")(db) + _yaml_rows("maintenance")(db)),
    ("strict-label rows in complaints", "hazard_categories.yaml, 02 sec 12", 8_293, 0,
     _db_rows_for("strict")),
    ("broad-label rows in complaints", "hazard_categories.yaml, 02 sec 12", 42_004, 0,
     _db_rows_for("broad")),

    # ---- the measured results -------------------------------------------
    ("ward-day base rate, strict (%)", "CLAUDE.md rule 3, 01, 02 sec 12", 1.56, 0.005,
     _base_rate),
    ("honest static precision@20 (IFS, %)", "01, DECISIONS.md, figures", 14.08, 0.005,
     _headroom("honest")),
    ("perfect-foresight ward ranking (IFS, %)", "01, 02 sec 19, DECISIONS.md", 15.66, 0.005,
     _headroom("foresight")),
    ("ward-level headroom gain (pts)", "01, DECISIONS.md", 1.58, 0.005,
     _headroom("gain")),
    ("total headroom to the ceiling (pts)", "01, DECISIONS.md", 23.64, 0.005,
     _headroom("headroom")),

    # ---- allocation ------------------------------------------------------
    ("total drainage spend (Rs)", "CLAUDE.md, 02 sec 24", 6_677_331_368, 1,
     _alloc("total")),
    ("median treated spend (Rs)", "CLAUDE.md, 02", 20_242_441, 1,
     _alloc("median_treated")),
    ("highest-spending ward", "02 sec 24", "Someshwara", 0, _alloc("max_ward")),
    ("highest spend (Rs)", "CLAUDE.md, 02", 631_617_283, 1, _alloc("max")),
    ("Jakkur drainage spend (Rs)", "CLAUDE.md, 02, figures", 494_203_600, 1,
     _alloc("jakkur")),
    ("Jakkur rank by spend", "CLAUDE.md ('2nd-highest')", 2, 0, _alloc("jakkur_rank")),

    # ---- the Jakkur case study ------------------------------------------
    ("Jakkur quarters", "figures README", 20, 0, _jakkur_index("n")),
    ("Jakkur index, first quarter", "figures README ('0.22')", 0.2179, 0.0001,
     _jakkur_index("first")),
    ("Jakkur index, last quarter", "figures README ('1.64')", 1.6362, 0.0001,
     _jakkur_index("last")),
    ("Jakkur mean rel_index", "figures README ('1.09'), check_parity", 1.0948, 0.0001,
     _jakkur_index("mean")),
    ("Jakkur quarters above the norm", "figures README ('10 of 20')", 10, 0,
     _jakkur_index("above")),

    # ---- the retraction, at its recovered specification ------------------
    ("dose-response, all 110 wards: coefficient", "CLAUDE.md, 02 sec 27.2", -0.0240, 0.0001,
     _dose("all_beta")),
    ("dose-response, all 110 wards: p", "CLAUDE.md, 02 sec 27.2", 0.0138, 0.0001,
     _dose("all_p")),
    ("dose-response, TREATED only: coefficient", "CLAUDE.md, DECISIONS.md", -0.0064, 0.0001,
     _dose("treated_beta")),
    ("dose-response, TREATED only: p", "CLAUDE.md, DECISIONS.md ('p = 0.83')", 0.8334, 0.0005,
     _dose("treated_p")),
    ("raw Spearman spend vs delta, treated", "CLAUDE.md ('-0.163, p = 0.099')", -0.1634, 0.0002,
     lambda _db: __import__("scipy.stats", fromlist=["spearmanr"]).spearmanr(
         (_p := pd.read_csv(ROOT / "data/reference/ward_dose_response_panel.csv"))
         [_p["spend"] > 0]["spend"],
         _p[_p["spend"] > 0]["delta"])[0]),

    # ---- reporting growth -------------------------------------------------
    ("complaint volume 2020 -> 2024 (ratio)", "DECISIONS.md ('doubled in four years')",
     2.28, 0.01,
     lambda db: db.execute(text(
         "SELECT (SELECT COUNT(*) FROM complaints WHERE YEAR(reported_at)=2024) / "
         "(SELECT COUNT(*) FROM complaints WHERE YEAR(reported_at)=2020)")).scalar()),
    ("wards with no register entry", "DECISIONS.md ('Ninety-six wards')", 96, 0,
     lambda _db: int((~pd.read_csv(ROOT / "data/reference/ward_crosswalk.csv")
                      ["in_flood_register"].astype(bool)).sum())),
    # ---- the label, and the generated artifacts --------------------------
    ("ward-day base rate, broad (%)", "CLAUDE.md rule 3, 02 sec 12", 7.99, 0.005,
     _broad_base_rate),
    ("ward polygons: features", "frontend/README.md, 03", 198, 0, _geojson("features")),
    ("ward polygons: size (KB)", "03 ('661 KB'), export script", 661, 0, _geojson("kb")),
    ("ward polygons: coordinate points", "REPORT.md ('36,369')", 36_369, 0,
     _geojson("points")),
    ("demo dump: INSERT statements", "04", 30, 0,
     lambda _db: sum(1 for line in (ROOT / "data/processed/demo_data.sql")
                     .read_text(encoding="utf-8").splitlines()
                     if line.startswith("INSERT INTO"))),
    ("demo dump: size (KB)", "03, 04, CLAUDE.md ('612 KB')", 612, 1,
     lambda _db: round((ROOT / "data/processed/demo_data.sql").stat().st_size / 1024)),
    ("demo dump: rows restored", "03, 04 ('4,820 rows')", 4_820, 0,
     lambda db: sum(db.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar()
                    for t in ("cities", "failure_types", "weather_cells", "locations",
                              "watchlist_snapshots", "ward_quarter_index",
                              "watchlist_entries", "emerging_watch",
                              "ward_allocation"))),
    # ---- profile sec 21: the agency-register agreement (it is in the paper) ---
    ("register: frozen top-20 on the register", "02 sec 21, paper", 16, 0,
     _register("hits")),
    ("register: coverage across 198 wards (%)", "02 sec 21 ('52%')", 51.5, 0.1,
     _register("coverage_pct")),
    ("register: expected under independence", "02 sec 21 ('10.3/20')", 10.3, 0.05,
     _register("expected")),
    ("register: hypergeometric p", "02 sec 21, paper ('0.0060')", 0.0060, 0.0001,
     _register("p_hyper")),
    ("register: mean events, register wards", "02 sec 21 ('24.7')", 24.7, 0.05,
     _register("mean_reg")),
    ("register: mean events, non-register", "02 sec 21 ('13.4')", 13.4, 0.05,
     _register("mean_nonreg")),
    ("register: Spearman events vs points", "02 sec 21 ('0.334')", 0.3343, 0.0005,
     _register("spearman")),
    ("register: Kendall tau", "02 sec 21 ('0.265')", 0.2650, 0.0005,
     _register("kendall")),
    ("register: Mann-Whitney one-sided p", "02 sec 21 ('0.0001')", 0.000113, 5e-6,
     _register("mw_p")),
    ("register: the four off-register top-20 wards", "02 sec 21",
     "Basavanapura, Hoodi, Jakkur, Someshwara", 0, _register("off_register")),

    # ---- profile sec 26.3: the quintile table, with its CIs -----------------
    ("quintile Q1 n / mean / p", "02 sec 26.3, DECISIONS.md", 21, 0,
     _quintile("Q1", "n")),
    ("quintile Q1 mean delta", "02 sec 26.3", 0.232, 0.0005, _quintile("Q1", "mean")),
    ("quintile Q1 95% CI low", "02 sec 26.3 ('+0.038')", 0.038, 0.0005,
     _quintile("Q1", "ci_lo")),
    ("quintile Q1 95% CI high", "02 sec 26.3 ('+0.425')", 0.425, 0.0005,
     _quintile("Q1", "ci_hi")),
    ("quintile Q1 p vs 0 (the only one < 0.05)", "02 sec 26.3", 0.022, 0.0005,
     _quintile("Q1", "p")),
    ("quintile Q5 mean delta", "02 sec 26.3 ('+0.105')", 0.105, 0.0005,
     _quintile("Q5", "mean")),
    ("quintile Q5 95% CI spans zero (low)", "02 sec 26.3 ('-0.142')", -0.142, 0.0005,
     _quintile("Q5", "ci_lo")),
    ("quintile Q5 p vs 0 (not significant)", "02 sec 26.3 ('0.385')", 0.385, 0.0005,
     _quintile("Q5", "p")),
    ("quintile Q3 mean delta", "02 sec 26.3 ('-0.146')", -0.146, 0.0005,
     _quintile("Q3", "mean")),
    ("quintile Q4 mean delta", "02 sec 26.3 ('-0.162')", -0.162, 0.0005,
     _quintile("Q4", "mean")),
    ("untreated n (not a valid control)", "02 sec 26.3, CLAUDE.md", 7, 0,
     _quintile("Untreated", "n")),
    ("quadratic term F (no non-monotonicity)", "02 sec 26.3 ('F = 1.26')", 1.26, 0.005,
     _quadratic_f),
    ("quadratic term coefficient", "02 sec 26.3 ('+0.0021')", 0.0021, 0.0001,
     _panel_ols(["log_spend", "log_spend_sq", "log_area", "pre"],
                "log_spend_sq", "beta")),
    ("baseline model R2", "02 sec 26.1 ('0.531')", 0.531, 0.0005,
     _panel_ols(["log_spend", "log_area", "pre"], "log_spend", "r2")),
    ("baseline: pre-period index coefficient", "02 sec 26.1 ('-0.7877')", -0.7877, 0.0001,
     _panel_ols(["log_spend", "log_area", "pre"], "pre", "beta")),
    ("baseline: log(area) coefficient", "02 sec 26.1 ('-0.0033')", -0.0033, 0.0001,
     _panel_ols(["log_spend", "log_area", "pre"], "log_area", "beta")),
    ("with growth control: log_spend", "02 sec 26.1 ('-0.0247')", -0.0247, 0.0001,
     _panel_ols(["log_spend", "log_area", "pre", "log_growth"], "log_spend", "beta")),
    ("with growth control: log_growth", "02 sec 26.1 ('-0.1065')", -0.1065, 0.0001,
     _panel_ols(["log_spend", "log_area", "pre", "log_growth"], "log_growth", "beta")),

    # ---- the citywide decline, with its instrument named -------------------
    ("citywide share decline (%), pooled first4 vs last4",
     "CLAUDE.md, DECISIONS.md, 01, 02 sec 22 ('22%')", -21.8, 0.05, _city_decline),
]

SLOW: list[Check] = [
    # Re-runs the whole re-rank on both bases; a few seconds, but it needs the
    # full complaint and weather history rather than just the derived tables.
    ("static precision@20, ERA5 (%)", "01 (reference table)", 13.55, 0.005,
     lambda db: _rerank(db, "era5", "static")),
    ("re-ranked precision@20, ERA5 (%)", "01 (reference table)", 13.70, 0.005,
     lambda db: _rerank(db, "era5", "reranked")),
    ("static precision@20, IFS (%)", "01 (lead table)", 14.08, 0.005,
     lambda db: _rerank(db, "ecmwf_ifs", "static")),
    ("re-ranked precision@20, IFS (%)", "01 (lead table)", 14.23, 0.005,
     lambda db: _rerank(db, "ecmwf_ifs", "reranked")),
]

_RERANK_CACHE: dict[str, dict] = {}


def _rerank(db, model: str, key: str) -> float:
    if model not in _RERANK_CACHE:
        from scripts.measure_reranked_baseline import _names, measure  # type: ignore
        from app.derived.watchlist import _ward_count
        from app.ingestion.base import resolve_city
        city = resolve_city(db, "Bengaluru")
        _RERANK_CACHE[model] = measure(
            db, city.city_id, model, _names(db, city.city_id),
            _ward_count(db, city.city_id))
    return _RERANK_CACHE[model][key] * 100


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slow", action="store_true",
                    help="also re-measure the static and re-ranked baselines")
    args = ap.parse_args()

    checks = CHECKS + (SLOW if args.slow else [])
    db = SessionLocal()
    failures: list[str] = []
    try:
        print(f"{'figure':<52}{'expected':>18}{'measured':>18}  where")
        print("-" * 116)
        for label, where, expected, tol, fn in checks:
            try:
                got = fn(db)
            except Exception as e:  # noqa: BLE001
                failures.append(f"{label}: could not compute ({type(e).__name__}: {e})")
                print(f"{label:<52}{expected!s:>18}{'ERROR':>18}  {where}")
                continue
            if isinstance(expected, str):
                ok = str(got) == expected
            elif tol == 0:
                ok = int(got) == int(expected)
            else:
                ok = abs(float(got) - float(expected)) <= tol
            shown = f"{got:,.4f}".rstrip("0").rstrip(".") if isinstance(got, float) \
                else f"{got:,}" if isinstance(got, int) else str(got)
            exp = f"{expected:,}" if isinstance(expected, int) else str(expected)
            print(f"{label:<52}{exp:>18}{shown:>18}  "
                  f"{'' if ok else '<-- MISMATCH  '}{where}")
            if not ok:
                failures.append(f"{label}: documented {expected!r}, measured {got!r} "
                                f"(appears in {where})")
    finally:
        db.close()

    print()
    if failures:
        print(f"FAILED - {len(failures)} of {len(checks)} figures do not match:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"PASSED - all {len(checks)} documented figures reproduce from primary sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
