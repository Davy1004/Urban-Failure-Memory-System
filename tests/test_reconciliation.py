"""Does the database pipeline reproduce the published analysis exactly?

Every number in docs/02-data-profile.md was computed by CSV-based scripts. If
the database pipeline computes the relative flooding index even slightly
differently, the dashboard will disagree with the paper and one of them will be
wrong — a divergence that is easy to introduce and very hard to notice later.

This test recomputes the index from the database and asserts it matches
`data/reference/ward_dose_response_panel.csv` exactly: same wards, same event
counts, same pre and post values.

It is skipped when the database is empty or the raw CSVs are absent, so a clean
checkout still passes; it is the loaded state it guards.
"""
import pathlib

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from app.db.session import engine
from app.ingestion.bbmp_complaints import TOTALS_PATH, load_hazard_map

REF = pathlib.Path(__file__).resolve().parents[1] / "data" / "reference"
PANEL = REF / "ward_dose_response_panel.csv"

# Exactly the windows used to build the published panel (profile §25.2).
Q_START, Q_END = "2020-04-01", "2025-04-01"
PRE_END = "2021-01-01"
SMOOTH = 0.5
MIN_EVENTS = 8


@pytest.fixture(scope="module")
def published():
    if not PANEL.exists():
        pytest.skip("published panel not present")
    return pd.read_csv(PANEL)


@pytest.fixture(scope="module")
def from_database():
    """Rebuild the relative index from the database plus the totals artifact."""
    if not TOTALS_PATH.exists():
        pytest.skip("ward_period_totals.csv not generated")

    hz = load_hazard_map()
    event_subs = sorted(s for s, (code, sev) in hz.by_sub_category.items()
                        if code == "WATERLOG" and sev == "event")

    with engine.connect() as c:
        n = c.execute(text("SELECT COUNT(*) FROM complaints")).scalar()
        if not n:
            pytest.skip("complaints table is empty")
        placeholders = ", ".join(f":s{i}" for i in range(len(event_subs)))
        rows = c.execute(
            text(
                "SELECT l.area_name AS ward, c.reported_at AS d "
                "FROM complaints c JOIN locations l "
                "  ON l.location_id = c.location_id "
                f"WHERE l.geom_level = 'ward' AND c.sub_category IN ({placeholders})"
            ),
            {f"s{i}": s for i, s in enumerate(event_subs)},
        ).all()

    ev = pd.DataFrame(rows, columns=["ward", "d"])
    ev["d"] = pd.to_datetime(ev["d"])
    ev = ev[(ev["d"] >= Q_START) & (ev["d"] < Q_END)]
    # A ward-DAY, not a complaint: the published panel counts distinct days.
    ev = ev.drop_duplicates(["ward", "d"])
    ev["period"] = ev["d"].dt.to_period("Q").astype(str)

    tot = pd.read_csv(TOTALS_PATH)
    tot = tot[(tot["period"] >= "2020Q2") & (tot["period"] <= "2025Q1")]

    wards = sorted(tot["ward"].unique())
    periods = sorted(tot["period"].unique())
    E = (ev.groupby(["ward", "period"]).size().unstack(fill_value=0)
         .reindex(index=wards, columns=periods, fill_value=0))
    T = (tot.pivot(index="ward", columns="period", values="total_complaints")
         .reindex(index=wards, columns=periods).fillna(0))

    city = E.sum(axis=0) / T.sum(axis=0)
    rel = (E + SMOOTH) / (T.mul(city, axis=1) + SMOOTH)

    pre_q = [p for p in periods if pd.Period(p, "Q").start_time < pd.Timestamp(PRE_END)]
    post_q = [p for p in periods if pd.Period(p, "Q").year >= 2023]

    out = pd.DataFrame({
        "ward": wards,
        "pre": rel[pre_q].mean(axis=1).values,
        "post": rel[post_q].mean(axis=1).values,
        "ev_pre": E[pre_q].sum(axis=1).values.astype(int),
        "ev_post": E[post_q].sum(axis=1).values.astype(int),
    })
    return out[(out["ev_pre"] + out["ev_post"]) >= MIN_EVENTS].reset_index(drop=True)


class TestDatabaseMatchesPublishedAnalysis:
    def test_same_ward_set(self, published, from_database):
        pub = set(published["ward"])
        db = set(from_database["ward"])
        assert db == pub, (
            f"ward set differs: {len(db - pub)} only in DB {sorted(db - pub)[:5]}, "
            f"{len(pub - db)} only in the panel {sorted(pub - db)[:5]}"
        )

    def test_same_ward_count(self, published, from_database):
        assert len(from_database) == len(published) == 110

    def test_event_counts_match_exactly(self, published, from_database):
        m = published.merge(from_database, on="ward", suffixes=("_pub", "_db"))
        for col in ("ev_pre", "ev_post"):
            bad = m[m[f"{col}_pub"] != m[f"{col}_db"]]
            assert bad.empty, (
                f"{col} differs for {len(bad)} ward(s): "
                + ", ".join(f"{r.ward} pub={getattr(r, col + '_pub')} "
                            f"db={getattr(r, col + '_db')}"
                            for r in bad.head(5).itertuples())
            )

    def test_relative_index_matches(self, published, from_database):
        m = published.merge(from_database, on="ward", suffixes=("_pub", "_db"))
        for col in ("pre", "post"):
            diff = (m[f"{col}_pub"] - m[f"{col}_db"]).abs()
            worst = m.loc[diff.idxmax()]
            assert diff.max() < 1e-9, (
                f"{col} index differs; worst is {worst['ward']}: "
                f"published {worst[f'{col}_pub']:.9f} vs database "
                f"{worst[f'{col}_db']:.9f} (max abs diff {diff.max():.3e})"
            )

    def test_totals_artifact_covers_every_ward(self):
        if not TOTALS_PATH.exists():
            pytest.skip("totals not generated")
        tot = pd.read_csv(TOTALS_PATH)
        assert tot["ward"].nunique() == 198
        assert (tot["total_complaints"] > 0).all()


class TestLoaderMatchesTheHazardMap:
    """The YAML records expected row counts; the database must agree."""

    def test_loaded_counts_match_the_yaml(self):
        hz = load_hazard_map()
        with engine.connect() as c:
            n = c.execute(text("SELECT COUNT(*) FROM complaints")).scalar()
            if not n:
                pytest.skip("complaints table is empty")
            by_code = dict(c.execute(text(
                "SELECT f.code, COUNT(*) FROM complaints c "
                "JOIN failure_types f ON f.failure_type_id = c.failure_type_id "
                "GROUP BY f.code")).all())
        assert by_code.get("WATERLOG") == hz.expected_rows["waterlog_broad"]
        assert by_code.get("GARBAGE") == hz.expected_rows["garbage"]

    def test_event_and_maintenance_split_matches_the_yaml(self):
        hz = load_hazard_map()
        ev = sorted(s for s, (c_, sev) in hz.by_sub_category.items()
                    if sev == "event")
        with engine.connect() as c:
            n = c.execute(text("SELECT COUNT(*) FROM complaints")).scalar()
            if not n:
                pytest.skip("complaints table is empty")
            ph = ", ".join(f":s{i}" for i in range(len(ev)))
            got = c.execute(
                text(f"SELECT COUNT(*) FROM complaints WHERE sub_category IN ({ph})"),
                {f"s{i}": s for i, s in enumerate(ev)}).scalar()
        assert got == hz.expected_rows["waterlog_event"]

    def test_timestamps_are_dates_not_datetimes(self):
        """The source lost its AM/PM marker, so any time component is fiction."""
        with engine.connect() as c:
            n = c.execute(text("SELECT COUNT(*) FROM complaints")).scalar()
            if not n:
                pytest.skip("complaints table is empty")
            with_time = c.execute(text(
                "SELECT COUNT(*) FROM complaints "
                "WHERE TIME(reported_at) <> '00:00:00'")).scalar()
        assert with_time == 0, f"{with_time} complaints carry a time component"

    def test_no_complaint_outside_the_source_window(self):
        with engine.connect() as c:
            n = c.execute(text("SELECT COUNT(*) FROM complaints")).scalar()
            if not n:
                pytest.skip("complaints table is empty")
            lo, hi = c.execute(text(
                "SELECT MIN(reported_at), MAX(reported_at) FROM complaints")).one()
        assert str(lo)[:10] == "2020-02-08"
        assert str(hi)[:10] == "2025-06-19"
