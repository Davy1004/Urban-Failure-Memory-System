"""The four dashboard endpoints, over a real database.

Two things are being checked, and the second matters more.

**That the endpoints work**: shapes, roles, 404s on a ward that does not exist.

**That the numbers cannot leave the API stripped of their context.** The
project's central risk is not a wrong figure, it is a right figure presented
so that it reads as something else — a 14% precision@20 without its ceiling, a
slope ranking read as acceleration, `delta_index` read as an effect of spend.
Those are asserted here as response-contract tests, because a frontend can drop
a caveat paragraph in a redesign and a required response field cannot.

Skips when the database is empty or the derived tables have not been built.
"""
import pathlib
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.enums import UserRole
from app.models.user import User

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _count(table: str) -> int:
    with engine.connect() as c:
        return int(c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar())


@pytest.fixture(scope="module", autouse=True)
def require_derived():
    for table in ("ward_quarter_index", "watchlist_snapshots", "emerging_watch",
                  "ward_allocation"):
        try:
            n = _count(table)
        except Exception as exc:                              # pragma: no cover
            pytest.skip(f"{table} not reachable: {exc}")
        if not n:
            pytest.skip(f"{table} is empty; run `python -m app.ingestion.cli derive`")


@pytest.fixture(scope="module")
def users():
    """One admin and one officer, removed again afterwards."""
    made = []
    with SessionLocal() as db:
        for role in (UserRole.ADMIN, UserRole.OFFICER):
            email = f"pytest-{role.value}@ufms.invalid"
            existing = db.execute(
                text("SELECT user_id FROM users WHERE email = :e"), {"e": email}
            ).scalar()
            if existing:
                made.append((role, int(existing)))
                continue
            u = User(email=email, name=f"pytest {role.value}",
                     password_hash=hash_password("not-a-real-password"),
                     role=role, is_active=True)
            db.add(u)
            db.commit()
            made.append((role, u.user_id))
        ids = dict(made)
    yield {role: create_access_token(str(uid), role.value)
           for role, uid in ids.items()}
    with SessionLocal() as db:
        for _, uid in ids.items():
            db.execute(text("DELETE FROM users WHERE user_id = :i"), {"i": uid})
        db.commit()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestAccess:
    """Read-only for officers, and nothing readable without a token."""

    @pytest.mark.parametrize("path", ["/api/v1/watchlist", "/api/v1/emerging",
                                      "/api/v1/allocation", "/api/v1/index",
                                      "/api/v1/index/Bellandur"])
    def test_requires_a_token(self, client, path):
        assert client.get(path).status_code == 401

    @pytest.mark.parametrize("path", ["/api/v1/watchlist", "/api/v1/emerging",
                                      "/api/v1/allocation", "/api/v1/index",
                                      "/api/v1/index/Bellandur"])
    def test_officers_can_read_every_screen(self, client, users, path):
        r = client.get(path, headers=_auth(users[UserRole.OFFICER]))
        assert r.status_code == 200, r.text

    def test_admins_can_read_too(self, client, users):
        r = client.get("/api/v1/watchlist", headers=_auth(users[UserRole.ADMIN]))
        assert r.status_code == 200


class TestIndexEndpoint:
    def test_series_by_ward_name(self, client, users):
        r = client.get("/api/v1/index/Bellandur",
                       headers=_auth(users[UserRole.OFFICER]))
        assert r.status_code == 200
        d = r.json()
        assert d["ward"] == "Bellandur"
        assert d["quarters"] == 20
        assert d["points"][0]["period"] == "2020Q2"
        assert d["points"][-1]["period"] == "2025Q1"

    def test_series_by_ward_number(self, client, users):
        by_name = client.get("/api/v1/index/Bellandur",
                             headers=_auth(users[UserRole.OFFICER])).json()
        by_no = client.get(f"/api/v1/index/{by_name['ward_no']}",
                           headers=_auth(users[UserRole.OFFICER])).json()
        assert by_no["location_id"] == by_name["location_id"]

    def test_every_point_shows_its_inputs(self, client, users):
        """The index is a benchmarked ratio. A screen that plots `rel_index`
        alone cannot show why a ward moved, so the inputs travel with it."""
        d = client.get("/api/v1/index/Bellandur",
                       headers=_auth(users[UserRole.OFFICER])).json()
        for p in d["points"]:
            assert p["total_complaints"] > 0
            assert p["city_share"] > 0
            assert abs(p["expected_event_days"]
                       - p["total_complaints"] * p["city_share"]) < 1e-9
        assert "Above 1.00" in d["definition"]
        assert "Normalising" in d["definition"]

    def test_unknown_ward_is_404_not_a_guess(self, client, users):
        r = client.get("/api/v1/index/Bellandurr",
                       headers=_auth(users[UserRole.OFFICER]))
        assert r.status_code == 404
        assert "not fuzzy-matched" in r.json()["error"]["message"]


class TestCityIndexEndpoint:
    """The choropleth's data: every ward, one quarter, in one response."""

    @pytest.fixture(scope="class")
    def payload(self, client, users):
        r = client.get("/api/v1/index", headers=_auth(users[UserRole.OFFICER]))
        assert r.status_code == 200, r.text
        return r.json()

    def test_every_ward_is_present(self, payload):
        """A ward missing from a choropleth reads as 'nothing happened here',
        which is a different and worse claim than 'no data'."""
        assert len(payload["wards"]) == 198
        assert len({w["ward_no"] for w in payload["wards"]}) == 198

    def test_defaults_to_the_latest_quarter(self, payload):
        assert payload["period"] == "2025Q1"
        assert payload["available_periods"][0] == "2020Q2"
        assert payload["available_periods"][-1] == "2025Q1"
        assert len(payload["available_periods"]) == 20

    def test_one_city_share_for_the_quarter(self, payload):
        """The share is the citywide aggregate, not a per-ward figure."""
        assert payload["city_share"] > 0
        for w in payload["wards"]:
            expected = w["total_complaints"] * payload["city_share"]
            assert abs(w["expected_event_days"] - expected) < 1e-9

    def test_a_named_quarter_can_be_requested(self, client, users):
        r = client.get("/api/v1/index?period=2022Q3",
                       headers=_auth(users[UserRole.OFFICER]))
        assert r.status_code == 200
        assert r.json()["period"] == "2022Q3"

    def test_an_unknown_quarter_is_404(self, client, users):
        r = client.get("/api/v1/index?period=2019Q1",
                       headers=_auth(users[UserRole.OFFICER]))
        assert r.status_code == 404
        assert "2020Q2" in r.json()["error"]["message"]

    def test_matches_the_per_ward_series(self, payload, client, users):
        one = client.get("/api/v1/index/Bellandur",
                         headers=_auth(users[UserRole.OFFICER])).json()
        last = one["points"][-1]
        row = next(w for w in payload["wards"] if w["ward"] == "Bellandur")
        assert last["period"] == payload["period"]
        assert row["rel_index"] == last["rel_index"]
        assert row["event_days"] == last["event_days"]


class TestWatchlistEndpoint:
    @pytest.fixture(scope="class")
    def payload(self, client, users):
        r = client.get("/api/v1/watchlist", headers=_auth(users[UserRole.OFFICER]))
        assert r.status_code == 200, r.text
        return r.json()

    def test_returns_the_frozen_list(self, payload):
        assert payload["k"] == 20
        assert len(payload["items"]) == 20
        assert payload["items"][0]["ward"] == "Bellandur"
        assert payload["items"][0]["rank_position"] == 1

    def test_context_carries_all_three_figures(self, payload):
        """The whole reason the snapshot table has metric columns."""
        c = payload["context"]
        assert c["precision_at_k"] is not None
        assert c["oracle_at_k"] is not None
        assert c["random_at_k"] is not None
        assert c["random_at_k"] < c["precision_at_k"] < c["oracle_at_k"]
        assert abs(c["precision_at_k"] - 0.140809) < 5e-7
        assert abs(c["oracle_at_k"] - 0.377206) < 5e-7

    def test_share_of_ceiling_is_computed_for_the_client(self, payload):
        c = payload["context"]
        assert abs(c["share_of_ceiling"] - c["precision_at_k"] / c["oracle_at_k"]) < 1e-9
        assert 0.35 < c["share_of_ceiling"] < 0.40

    def test_the_reading_travels_with_the_numbers(self, payload):
        assert "all three" in payload["context"]["reading"]

    def test_test_window_is_described(self, payload):
        c = payload["context"]
        assert c["test_rain_days"] == 136
        assert c["weather_model"] == "ecmwf_ifs"
        assert c["rain_threshold_mm"] == 2.5


class TestEmergingEndpoint:
    @pytest.fixture(scope="class")
    def payload(self, client, users):
        r = client.get("/api/v1/emerging", headers=_auth(users[UserRole.OFFICER]))
        assert r.status_code == 200, r.text
        return r.json()

    def test_ranked_list(self, payload):
        assert payload["eligible_wards"] == 103
        assert payload["flagged"] == 10
        assert len(payload["items"]) == 103
        assert payload["items"][0]["rank_position"] == 1

    def test_label_is_not_accelerating(self, payload):
        assert payload["label"] == "chronically_above_norm"
        joined = " ".join(payload["caveats"]).lower()
        assert "not 'accelerating'" in joined

    def test_no_ground_truth_is_claimed(self, payload):
        """first_listed_year is NULL for all 398 register points, so a flag
        cannot be validated against the city's own additions."""
        assert payload["ground_truth_available"] is False
        assert any("ground truth" in c.lower() for c in payload["caveats"])

    def test_evidence_shows_level_persistence_not_acceleration(self, payload):
        e = payload["evidence"]
        assert e["flagged_n"] == 10
        assert e["flagged_above_norm"] == 10
        assert e["p_vs_other_wards"] < 0.001
        assert e["p_vs_own_first_half"] > 0.05
        assert e["flagged_half2_level"] > e["all_half2_level"]

    def test_every_item_carries_its_p_value(self, payload):
        """A rank without a p-value invites reading the ranking as a discovery.
        BH-FDR over 103 wards leaves zero survivors."""
        for item in payload["items"]:
            assert 0.0 <= item["half1_p"] <= 1.0
            assert 0.0 <= item["full_p"] <= 1.0

    def test_off_register_filter_is_the_prespecified_pool(self, client, users):
        r = client.get("/api/v1/emerging?off_register=true",
                       headers=_auth(users[UserRole.OFFICER]))
        items = r.json()["items"]
        assert items and all(not i["on_register"] for i in items)
        assert "Jakkur" in [i["ward"] for i in items]

    def test_flagged_only_filter(self, client, users):
        r = client.get("/api/v1/emerging?flagged_only=true",
                       headers=_auth(users[UserRole.OFFICER]))
        items = r.json()["items"]
        assert len(items) == 10 and all(i["is_flagged"] for i in items)


class TestAllocationEndpoint:
    @pytest.fixture(scope="class")
    def payload(self, client, users):
        r = client.get("/api/v1/allocation", headers=_auth(users[UserRole.OFFICER]))
        assert r.status_code == 200, r.text
        return r.json()

    def test_panel(self, payload):
        assert len(payload["items"]) == 110
        assert payload["finding"]["n_treated"] == 103
        assert payload["finding"]["n_untreated"] == 7
        assert payload["items"][0]["ward"] == "Someshwara"   # ordered by spend

    def test_the_finding_is_the_allocation_correlations(self, payload):
        f = payload["finding"]
        assert abs(f["spend_vs_area"]["rho"] - 0.474) < 0.001
        assert abs(f["spend_vs_pre_index"]["rho"] - 0.082) < 0.001
        assert f["spend_vs_pre_index"]["p"] > 0.30
        assert abs(f["spend_vs_events_controlling_area"]["rho"] + 0.050) < 0.001

    def test_no_coefficient_is_returned(self, payload):
        """§27.2 retracted the dose-response; §28 closed the analysis."""
        blob = str(payload["finding"]).lower()
        assert "coefficient" not in blob and "dose" not in blob
        assert "RETRACTED" in payload["retraction"]

    def test_delta_is_labelled_as_descriptive(self, payload, client, users):
        schema = client.get("/openapi.json").json()
        desc = (schema["components"]["schemas"]["AllocationItem"]
                ["properties"]["delta_index"]["description"])
        assert "NOT an effect of spend" in desc

    def test_headline_names_area_not_need(self, payload):
        h = payload["headline"]
        assert "ward size" in h and "+0.474" in h

    def test_treated_only_filter(self, client, users):
        r = client.get("/api/v1/allocation?treated_only=true",
                       headers=_auth(users[UserRole.OFFICER]))
        items = r.json()["items"]
        assert len(items) == 103 and all(i["is_treated"] for i in items)
