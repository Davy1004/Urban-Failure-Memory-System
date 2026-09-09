"""Do the derived tables reproduce the published analysis exactly?

`tests/test_reconciliation.py` guards the loader and it caught nothing, because
the loader was right. This file is where that pattern earns its keep: four
computations the paper already published are reimplemented here against a
database instead of a dataframe, and every one of them has a way to be subtly
wrong that no unit test would notice.

Each table is checked against the committed reference CSV that recorded what
the original analysis scripts produced:

    ward_quarter_index  ->  ward_dose_response_panel.csv, ward_relative_trends.csv
    watchlist_*         ->  profile §14.2's frozen top-20 and §17.3 variant B
    emerging_watch      ->  ward_persistence.csv, ward_relative_trends.csv
    ward_allocation     ->  ward_dose_response_panel.csv

Tolerance is 1e-9 on anything the published panel states, which is why the
index columns are stored at 16 decimal places rather than rounded for display.

The whole module skips when the database is empty or the derived tables have
not been built, so a clean checkout still passes; it is the loaded state it
guards.
"""
import pathlib

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from app.db.session import engine
from app.derived import (
    EMERGING_FLAG_TOP_N, WATCHLIST_AS_OF, WATCHLIST_K, WORKS_WINDOW_END,
    WORKS_WINDOW_START,
)
from app.models.derived import CHRONICALLY_ABOVE_NORM

ROOT = pathlib.Path(__file__).resolve().parents[1]
REF = ROOT / "data" / "reference"
PANEL = REF / "ward_dose_response_panel.csv"
TRENDS = REF / "ward_relative_trends.csv"
PERSISTENCE = REF / "ward_persistence.csv"

TOL = 1e-9

# Profile §17.3 variant B: IFS city-mean rain days, all 198 wards ranked.
# The random floor is the analytic expectation (mean events per night / 198);
# the profile quotes 4.80% from a simulated draw, which is the same number.
EXPECTED_PRECISION_AT_20 = 0.140809
EXPECTED_ORACLE_AT_20 = 0.377206
EXPECTED_RANDOM_AT_20 = 0.047868
EXPECTED_RAIN_DAYS = 136
EXPECTED_TEST_EVENTS = 1289

# Profile §14.2, in rank order. Frozen on events to 2023-12-31, ties by name.
FROZEN_TOP_20 = [
    "Bellandur", "Horamavu", "Thanisandra", "Begur", "Ramamurthy Nagar",
    "Hoodi", "Dodda Bidarkallu", "Singasandra", "Someshwara", "Varthur",
    "Rajarajeshwari Nagar", "Bilekahalli", "Jakkur", "HBR Layout",
    "Doddanekkundi", "HSR Layout", "Hagadooru", "Byatarayanapura",
    "Basavanapura", "Herohalli",
]

# Profile §24.1 and §25.1: what the 198 work-order files must parse to.
WO_MAIN_ROWS = 45_737
WO_LEGACY_ROWS = 4_178
WO_DRAINAGE_MAIN = 16_648        # matches hazard_categories.yaml union_rows
WO_IN_WINDOW_MAIN = 1_353
WO_IN_WINDOW_LEGACY = 125


def _table_count(table: str) -> int:
    with engine.connect() as c:
        return int(c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar())


def _require(table: str) -> None:
    try:
        n = _table_count(table)
    except Exception as exc:                                  # pragma: no cover
        pytest.skip(f"{table} not reachable: {exc}")
    if not n:
        pytest.skip(f"{table} is empty; run `python -m app.ingestion.cli derive`")


def _read(sql: str, cols: list) -> pd.DataFrame:
    with engine.connect() as c:
        return pd.DataFrame(c.execute(text(sql)).all(), columns=cols)


@pytest.fixture(scope="module")
def published():
    if not PANEL.exists():
        pytest.skip("published panel not present")
    return pd.read_csv(PANEL)


@pytest.fixture(scope="module")
def trends():
    if not TRENDS.exists():
        pytest.skip("ward_relative_trends.csv not present")
    return pd.read_csv(TRENDS)


@pytest.fixture(scope="module")
def persistence():
    if not PERSISTENCE.exists():
        pytest.skip("ward_persistence.csv not present")
    return pd.read_csv(PERSISTENCE, index_col=0)


@pytest.fixture(scope="module")
def index_frame():
    _require("ward_quarter_index")
    df = _read(
        "SELECT l.area_name AS ward, q.period_start, q.event_days, "
        "       q.total_complaints, q.city_share, q.smoothing, q.rel_index "
        "FROM ward_quarter_index q "
        "JOIN locations l ON l.location_id = q.location_id "
        "WHERE q.period_type = 'quarter'",
        ["ward", "period_start", "event_days", "total_complaints",
         "city_share", "smoothing", "rel_index"],
    )
    df["period_start"] = pd.to_datetime(df["period_start"])
    df["period"] = df["period_start"].dt.to_period("Q").astype(str)
    for col in ("city_share", "smoothing", "rel_index"):
        df[col] = df[col].astype(float)
    return df


def _wide(df: pd.DataFrame, value: str) -> pd.DataFrame:
    return df.pivot(index="ward", columns="period", values=value).sort_index(axis=1)


class TestWardQuarterIndex:
    """The index is the quantity everything else is built on."""

    def test_shape_is_the_published_window(self, index_frame):
        periods = sorted(index_frame["period"].unique())
        assert index_frame["ward"].nunique() == 198
        assert periods[0] == "2020Q2" and periods[-1] == "2025Q1"
        assert len(periods) == 20
        assert len(index_frame) == 198 * 20

    def test_rel_is_recomputable_from_the_stored_components(self, index_frame):
        """The point of storing city_share: no second pass over `complaints`."""
        d = index_frame
        expect = ((d["event_days"] + d["smoothing"])
                  / (d["total_complaints"] * d["city_share"] + d["smoothing"]))
        worst = (expect - d["rel_index"]).abs().max()
        assert worst < TOL, f"rel_index does not match its own inputs: {worst:.3e}"

    def test_city_share_is_the_citywide_ratio(self, index_frame):
        """One share per quarter, and it is the city aggregate, not a mean of
        ward ratios — the difference is the whole city-trend null."""
        for period, g in index_frame.groupby("period"):
            assert g["city_share"].nunique() == 1, f"{period} has several shares"
            expect = g["event_days"].sum() / g["total_complaints"].sum()
            assert abs(g["city_share"].iloc[0] - expect) < TOL, period

    def test_one_is_the_city_norm(self, index_frame):
        """The interpretation the whole dashboard rests on: above 1 means the
        ward had more event-days than the citywide mix predicts for its
        complaint volume, below 1 means fewer. Stated as a sign identity
        because it is exact — smoothing moves the magnitude away from 1 when
        the expected count is small, but never the side."""
        d = index_frame
        expected = d["total_complaints"] * d["city_share"]
        above = d["rel_index"] > 1.0
        assert (above == (d["event_days"] > expected)).all()
        assert ((d["rel_index"] == 1.0) == (d["event_days"] == expected)).all()

    def test_matches_the_published_relative_trends(self, index_frame, trends):
        rel = _wide(index_frame, "rel_index")
        ev = _wide(index_frame, "event_days")
        tot = _wide(index_frame, "total_complaints")
        cols = list(rel.columns)
        ref = trends.set_index("ward")

        checks = {
            "rel_first4": rel[cols[:4]].mean(axis=1),
            "rel_last4": rel[cols[-4:]].mean(axis=1),
            "events": ev.sum(axis=1),
            "ev_first4": ev[cols[:4]].sum(axis=1),
            "ev_last4": ev[cols[-4:]].sum(axis=1),
            "co_first4": tot[cols[:4]].sum(axis=1),
            "co_last4": tot[cols[-4:]].sum(axis=1),
        }
        for name, got in checks.items():
            diff = (got.reindex(ref.index) - ref[name]).abs()
            assert diff.max() < TOL, (
                f"{name} differs; worst is {diff.idxmax()} "
                f"({diff.max():.3e})"
            )

    def test_matches_the_published_dose_response_panel(self, index_frame, published):
        """pre, post and both event counts, exactly, on all 110 panel wards."""
        rel = _wide(index_frame, "rel_index")
        ev = _wide(index_frame, "event_days")
        cols = list(rel.columns)
        pre = [c for c in cols if c < "2021Q1"]
        post = [c for c in cols if c >= "2023Q1"]
        assert len(pre) == 3 and len(post) == 9

        got = pd.DataFrame({
            "pre": rel[pre].mean(axis=1), "post": rel[post].mean(axis=1),
            "ev_pre": ev[pre].sum(axis=1), "ev_post": ev[post].sum(axis=1),
            "ev_all": ev.sum(axis=1),
        })
        ref = published.set_index("ward")
        assert set(ref.index) <= set(got.index)
        for col in ("pre", "post", "ev_pre", "ev_post", "ev_all"):
            diff = (got[col].reindex(ref.index) - ref[col]).abs()
            assert diff.max() < TOL, (
                f"{col} differs; worst is {diff.idxmax()}: published "
                f"{ref.loc[diff.idxmax(), col]} vs database "
                f"{got.loc[diff.idxmax(), col]} ({diff.max():.3e})"
            )


class TestWatchlist:
    """The list, and the three numbers that stop it being misread."""

    @pytest.fixture(scope="class")
    def snapshot(self):
        _require("watchlist_snapshots")
        rows = _read(
            "SELECT snapshot_id, as_of_date, k, test_rain_days, test_events, "
            "       precision_at_k, oracle_at_k, random_at_k, weather_model, "
            "       rain_threshold_mm "
            "FROM watchlist_snapshots ORDER BY as_of_date DESC LIMIT 1",
            ["snapshot_id", "as_of_date", "k", "test_rain_days", "test_events",
             "precision_at_k", "oracle_at_k", "random_at_k", "weather_model",
             "rain_threshold_mm"],
        )
        return rows.iloc[0]

    @pytest.fixture(scope="class")
    def entries(self, snapshot):
        return _read(
            "SELECT e.rank_position, l.area_name, e.prior_events, e.test_events "
            "FROM watchlist_entries e JOIN locations l "
            "  ON l.location_id = e.location_id "
            f"WHERE e.snapshot_id = {int(snapshot.snapshot_id)} "
            "ORDER BY e.rank_position",
            ["rank_position", "area_name", "prior_events", "test_events"],
        )

    def test_the_frozen_list_is_the_published_one(self, entries):
        assert entries["area_name"].tolist() == FROZEN_TOP_20

    def test_the_list_is_ranked_by_prior_events(self, entries):
        assert entries["prior_events"].is_monotonic_decreasing
        assert entries["prior_events"].iloc[0] == 156      # Bellandur, §14.2

    def test_held_out_window_is_the_published_one(self, snapshot):
        assert snapshot.as_of_date == WATCHLIST_AS_OF
        assert int(snapshot.k) == WATCHLIST_K
        assert int(snapshot.test_rain_days) == EXPECTED_RAIN_DAYS
        assert int(snapshot.test_events) == EXPECTED_TEST_EVENTS
        assert snapshot.weather_model == "ecmwf_ifs"
        assert float(snapshot.rain_threshold_mm) == 2.5

    def test_the_three_metrics_reproduce(self, snapshot):
        for col, expected in (("precision_at_k", EXPECTED_PRECISION_AT_20),
                              ("oracle_at_k", EXPECTED_ORACLE_AT_20),
                              ("random_at_k", EXPECTED_RANDOM_AT_20)):
            got = float(getattr(snapshot, col))
            assert abs(got - expected) < 5e-7, f"{col}: {got} vs {expected}"

    def test_context_is_stored_not_just_the_list(self, snapshot):
        """A screen showing only the list invites the misreading the project
        spent six sessions disproving, so all three must be present."""
        assert snapshot.precision_at_k is not None
        assert snapshot.oracle_at_k is not None
        assert snapshot.random_at_k is not None
        assert (float(snapshot.random_at_k) < float(snapshot.precision_at_k)
                < float(snapshot.oracle_at_k)), (
            "the ordering random < achieved < ceiling is what makes the figure "
            "readable; if it inverts, something is wrong with the scoring"
        )

    def test_the_ceiling_is_well_below_one(self, snapshot):
        """A median rain night carries ~6 events citywide, so 20 slots cannot
        all be right. If the oracle ever approaches 1.0 the label or the
        rain-day filter has changed underneath us."""
        assert 0.3 < float(snapshot.oracle_at_k) < 0.5


class TestEmergingWatch:
    @pytest.fixture(scope="class")
    def watch(self):
        _require("emerging_watch")
        df = _read(
            "SELECT l.area_name AS ward, e.rank_position, e.event_days, "
            "       e.half1_slope, e.half1_p, e.half1_level, e.half2_level, "
            "       e.half2_slope, e.level_delta, e.full_slope, e.full_p, "
            "       e.is_flagged, e.on_register, e.label "
            "FROM emerging_watch e JOIN locations l "
            "  ON l.location_id = e.location_id",
            ["ward", "rank_position", "event_days", "half1_slope", "half1_p",
             "half1_level", "half2_level", "half2_slope", "level_delta",
             "full_slope", "full_p", "is_flagged", "on_register", "label"],
        )
        for col in ("half1_slope", "half1_p", "half1_level", "half2_level",
                    "half2_slope", "level_delta", "full_slope", "full_p"):
            df[col] = df[col].astype(float)
        return df.set_index("ward")

    def test_eligible_pool_is_the_published_one(self, watch, persistence):
        assert len(watch) == 103
        assert set(watch.index) == set(persistence.index)
        assert (watch["event_days"] >= 15).all()

    def test_halves_match_ward_persistence(self, watch, persistence):
        for mine, theirs in (("half1_slope", "slope1"), ("half1_p", "p1"),
                             ("half1_level", "lvl1"), ("half2_level", "lvl2"),
                             ("half2_slope", "slope2"), ("level_delta", "delta")):
            diff = (watch[mine].reindex(persistence.index) - persistence[theirs]).abs()
            assert diff.max() < TOL, (
                f"{mine} differs from {theirs}; worst is {diff.idxmax()} "
                f"({diff.max():.3e})"
            )

    def test_full_window_slope_matches_the_published_trends(self, watch, trends):
        ref = trends.set_index("ward").reindex(watch.index)
        for mine, theirs in (("full_slope", "rel_slope"), ("full_p", "rel_p")):
            diff = (watch[mine] - ref[theirs]).abs()
            assert diff.max() < TOL, f"{mine}: worst {diff.idxmax()} {diff.max():.3e}"

    def test_the_null_is_the_city_trend_not_zero(self, watch, trends):
        """Testing against zero gave 0 rising / 10 declining; against the city
        trend the same data gives 9 / 4. The stored slope must be the second."""
        ref = trends.set_index("ward").reindex(watch.index)
        rising = int(((watch["full_slope"] > 0) & (watch["full_p"] < 0.05)).sum())
        declining = int(((watch["full_slope"] < 0) & (watch["full_p"] < 0.05)).sum())
        assert (rising, declining) == (9, 4), (
            f"got {rising} rising / {declining} declining; 0/10 means the slope "
            f"was computed on the raw share against a zero null"
        )
        # And it is not the same series as the un-benchmarked share.
        assert not np.allclose(watch["full_slope"], ref["share_slope"])

    def test_ranked_by_first_half_slope(self, watch):
        ordered = watch.sort_values("rank_position")
        assert ordered["half1_slope"].is_monotonic_decreasing
        assert ordered["rank_position"].tolist() == list(range(1, len(watch) + 1))

    def test_flag_is_a_rank_cut(self, watch):
        """Not a significance cut: BH-FDR over 103 wards leaves zero survivors,
        so a p-value gate would flag nothing at all (profile §23.3)."""
        assert int(watch["is_flagged"].sum()) == EMERGING_FLAG_TOP_N
        assert set(watch.loc[watch["is_flagged"].astype(bool), "rank_position"]) == \
            set(range(1, EMERGING_FLAG_TOP_N + 1))

    def test_label_is_chronically_above_norm(self, watch):
        assert (watch["label"] == CHRONICALLY_ABOVE_NORM).all()

    def test_level_persistence_is_what_holds(self, watch):
        """The claim is that flagged wards stay above the city norm, and this
        is the measurement behind it (profile §25.1)."""
        flagged = watch[watch["is_flagged"].astype(bool)]
        assert len(flagged) == EMERGING_FLAG_TOP_N
        assert (flagged["half2_level"] > 1.0).all(), "10 of 10 finished above norm"
        assert abs(flagged["half2_level"].mean() - 1.77) < 0.01
        assert abs(watch["half2_level"].mean() - 1.16) < 0.01

    def test_flagged_wards_do_not_accelerate(self, watch):
        """The detector does NOT show wards continuing to worsen — 8 of 10 rise
        in level but not significantly against their own first half. If this
        ever became decisive the label would need to change with it."""
        flagged = watch[watch["is_flagged"].astype(bool)]
        from scipy import stats
        _, p = stats.wilcoxon(flagged["half2_level"], flagged["half1_level"],
                              alternative="greater")
        assert p > 0.05, f"flagged wards now exceed their own first half (p={p})"

    def test_register_flag_comes_from_the_crosswalk(self, watch):
        """`locations.is_known_hotspot` is set on the 398 register POINTS, so
        every ward row carries FALSE. Reading it there would mark all 103 wards
        off-register and quietly widen the pre-specified emerging pool."""
        assert int(watch["on_register"].sum()) > 0
        assert not watch.loc["Jakkur", "on_register"]
        assert watch.loc["Bharathi Nagar", "on_register"]


class TestWardAllocation:
    @pytest.fixture(scope="class")
    def alloc(self):
        _require("ward_allocation")
        df = _read(
            "SELECT l.area_name AS ward, a.window_start, a.window_end, "
            "       a.drainage_works, a.drainage_spend, a.ward_area_sqkm, "
            "       a.event_days_pre, a.event_days_post, a.event_days_total, "
            "       a.pre_index, a.post_index, a.delta_index, a.is_treated "
            "FROM ward_allocation a JOIN locations l "
            "  ON l.location_id = a.location_id",
            ["ward", "window_start", "window_end", "drainage_works",
             "drainage_spend", "ward_area_sqkm", "event_days_pre",
             "event_days_post", "event_days_total", "pre_index", "post_index",
             "delta_index", "is_treated"],
        )
        for col in ("drainage_spend", "ward_area_sqkm", "pre_index",
                    "post_index", "delta_index"):
            df[col] = df[col].astype(float)
        df["is_treated"] = df["is_treated"].astype(bool)
        return df.set_index("ward")

    def test_panel_is_the_published_one(self, alloc, published):
        assert len(alloc) == 110
        assert set(alloc.index) == set(published["ward"])
        assert int(alloc["is_treated"].sum()) == 103
        assert int((~alloc["is_treated"]).sum()) == 7

    def test_window_is_the_published_one(self, alloc):
        assert (alloc["window_start"] == WORKS_WINDOW_START).all()
        assert (alloc["window_end"] == WORKS_WINDOW_END).all()

    def test_spend_area_and_index_match_the_panel(self, alloc, published):
        ref = published.set_index("ward")
        for mine, theirs, tol in (("drainage_spend", "spend", 0.005),
                                  ("ward_area_sqkm", "area", TOL),
                                  ("pre_index", "pre", TOL),
                                  ("post_index", "post", TOL),
                                  ("delta_index", "delta", TOL),
                                  ("event_days_pre", "ev_pre", TOL),
                                  ("event_days_post", "ev_post", TOL),
                                  ("event_days_total", "ev_all", TOL)):
            diff = (alloc[mine].reindex(ref.index) - ref[theirs]).abs()
            assert diff.max() < tol, (
                f"{mine} differs from {theirs}; worst is {diff.idxmax()}: "
                f"published {ref.loc[diff.idxmax(), theirs]} vs database "
                f"{alloc.loc[diff.idxmax(), mine]}"
            )

    def test_the_top_spenders_are_the_published_ones(self, alloc):
        """Profile §24.4, plus ward 187 which the legacy-schema recovery added
        after that table was written."""
        top = alloc["drainage_spend"].sort_values(ascending=False)
        assert top.index[0] == "Someshwara" and abs(top.iloc[0] - 631_617_283) < 1
        assert top.index[1] == "Jakkur" and abs(top.iloc[1] - 494_203_600) < 1
        assert top.index[2] == "Ullalu" and abs(top.iloc[2] - 474_788_529) < 1

    def test_allocation_summary_reproduces_the_finding(self):
        from app.db.session import SessionLocal
        from app.derived.allocation import allocation_summary

        with SessionLocal() as db:
            city_id = db.execute(
                text("SELECT city_id FROM cities WHERE name = 'Bengaluru'")
            ).scalar_one()
            s = allocation_summary(db, city_id)

        # Spend tracks ward size, not flooding need. This is the finding.
        assert abs(s["spend_vs_area"]["rho"] - 0.474) < 0.001
        assert s["spend_vs_area"]["p"] < 0.0001
        assert abs(s["spend_vs_pre_index"]["rho"] - 0.082) < 0.001
        assert s["spend_vs_pre_index"]["p"] > 0.30, "the confound must stay absent"

        # And the targeting objection: raw +0.274, gone once area is controlled.
        assert abs(s["spend_vs_absolute_events"]["rho"] - 0.274) < 0.001
        assert abs(s["area_vs_absolute_events"]["rho"] - 0.649) < 0.001
        partial = s["spend_vs_events_controlling_area"]
        assert abs(partial["rho"] - (-0.050)) < 0.001
        assert partial["p"] > 0.5

    def test_no_outcome_estimate_is_exposed(self):
        """§27.2 retracted the dose-response and §28 closed the analysis. If a
        coefficient on spend ever appears in this payload it is a regression,
        not a feature."""
        from app.db.session import SessionLocal
        from app.derived.allocation import allocation_summary

        with SessionLocal() as db:
            city_id = db.execute(
                text("SELECT city_id FROM cities WHERE name = 'Bengaluru'")
            ).scalar_one()
            s = allocation_summary(db, city_id)
        banned = [k for k in s if any(w in k.lower()
                                      for w in ("coef", "effect", "dose", "beta"))]
        assert not banned, f"allocation_summary exposes an outcome estimate: {banned}"


class TestWorkOrderParsing:
    """The one data source independent of the complaint feed, and three
    parsing facts each of which was a wrong number before it was a fixed one."""

    @pytest.fixture(scope="class")
    def works(self):
        from app.derived.work_orders import WORK_ORDER_DIR, load_work_orders
        if not WORK_ORDER_DIR.exists():
            pytest.skip("data/raw/work_orders not present")
        return load_work_orders(WORK_ORDER_DIR)

    def test_all_198_files_parse(self, works):
        assert works.rows["ward_no"].nunique() == 198
        main = works.rows[works.rows["schema"] == "main"]
        legacy = works.rows[works.rows["schema"] == "legacy"]
        assert len(main) == WO_MAIN_ROWS
        assert len(legacy) == WO_LEGACY_ROWS
        assert legacy["ward_no"].min() == 184 and legacy["ward_no"].max() == 198

    def test_drainage_classification_matches_the_yaml(self, works):
        import yaml
        from app.ingestion.bbmp_complaints import HAZARD_YAML

        doc = yaml.safe_load(HAZARD_YAML.read_text(encoding="utf-8"))
        main = works.rows[works.rows["schema"] == "main"]
        assert int(main["is_drainage"].sum()) == WO_DRAINAGE_MAIN
        assert WO_DRAINAGE_MAIN == doc["work_orders"]["union_rows"]
        assert len(works.rows) == doc["work_orders"]["total_work_order_rows"]

    def test_legacy_dates_come_from_br_not_cbr(self, works):
        """CBR is the bill-clearance date roughly two years later; using it
        would put most of the legacy block outside the window entirely."""
        legacy = works.rows[works.rows["schema"] == "legacy"]
        assert legacy["completed_on"].notna().mean() > 0.99
        in_window = works.drainage_in_window(WORKS_WINDOW_START, WORKS_WINDOW_END)
        assert int((in_window["schema"] == "legacy").sum()) == WO_IN_WINDOW_LEGACY
        assert int((in_window["schema"] == "main").sum()) == WO_IN_WINDOW_MAIN

    def test_spend_is_nett_not_gross(self, works):
        """Nett is after deductions and it is what the panel was built on."""
        spend = works.spend_by_ward(WORKS_WINDOW_START, WORKS_WINDOW_END)
        assert abs(float(spend.loc[spend["ward_no"] == 3, "drainage_spend"].iloc[0])
                   - 631_617_283) < 1
