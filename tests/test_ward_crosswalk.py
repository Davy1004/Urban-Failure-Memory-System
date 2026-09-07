"""Tests for the ward crosswalk artifact and its loader-side rule.

The committed CSV is checked as data, not just the code that reads it — the
artifact is the deliverable, and a hand-edited CSV is exactly the kind of file
that drifts silently.
"""
import csv
import pathlib

import pandas as pd
import pytest

from app.ingestion.ward_crosswalk import (
    CROSSWALK_PATH, N_BBMP_WARDS, VALID_METHODS, WardCrosswalk, WardMapping,
    apply_to_ward_series, haversine_m, load_crosswalk,
)

# Bengaluru bounding box, generous.
LAT_RANGE = (12.7, 13.3)
LON_RANGE = (77.3, 77.9)


@pytest.fixture(scope="module")
def cw():
    return load_crosswalk()


def _m(name, no=None, rname=None, method="exact", notes="n",
       lat=12.97, lon=77.59, reg=False):
    return WardMapping(name, no, rname, "West", lat, lon, 1.0, method, reg, None, notes)


class TestCommittedArtifact:
    def test_file_exists_and_covers_every_ward(self, cw):
        assert len(cw) == N_BBMP_WARDS

    def test_every_complaint_ward_appears_exactly_once(self):
        with CROSSWALK_PATH.open(newline="", encoding="utf-8") as fh:
            names = [r["complaint_ward_name"] for r in csv.DictReader(fh)]
        assert len(names) == N_BBMP_WARDS
        assert len(set(names)) == N_BBMP_WARDS

    def test_ward_numbers_cover_1_to_198_exactly(self, cw):
        """The whole point of moving off the register: full coverage."""
        nos = {r.bbmp_ward_no for r in cw}
        assert nos == set(range(1, N_BBMP_WARDS + 1))

    def test_matches_the_ward_names_actually_in_the_csvs(self, cw):
        raw = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
        files = sorted(raw.glob("bbmp_grievances_*.csv"))
        if not files:
            pytest.skip("raw grievance CSVs not present (they are gitignored)")
        seen = set()
        for f in files:
            s = pd.read_csv(f, dtype=str, usecols=["Ward Name"],
                            keep_default_na=False, na_values=["", "NON Ward"])
            seen |= set(s["Ward Name"].dropna().unique())
        missing = seen - {r.complaint_ward_name for r in cw}
        assert not missing, f"ward names in the data but not the crosswalk: {sorted(missing)}"

    def test_no_ward_number_claimed_twice(self, cw):
        nos = [r.bbmp_ward_no for r in cw]
        assert len(nos) == len(set(nos))

    def test_every_ward_has_a_centroid_inside_bengaluru(self, cw):
        for r in cw:
            assert r.has_centroid, r.complaint_ward_name
            assert LAT_RANGE[0] < r.centroid_lat < LAT_RANGE[1], r.complaint_ward_name
            assert LON_RANGE[0] < r.centroid_lon < LON_RANGE[1], r.complaint_ward_name

    def test_centroids_are_distinct(self, cw):
        pts = {(round(r.centroid_lat, 5), round(r.centroid_lon, 5)) for r in cw}
        assert len(pts) == N_BBMP_WARDS

    def test_manual_rows_all_carry_a_note(self, cw):
        for r in cw:
            if r.match_method == "manual":
                assert len(r.notes) > 20, f"{r.complaint_ward_name} has a thin note"

    def test_register_membership_matches_the_registers_own_coverage(self, cw):
        """The flood register covers 103 wards; 102 map to a complaint ward."""
        assert len(cw.register_wards) == 102
        assert len(cw.non_register_wards) == 96
        assert cw.register_wards | cw.non_register_wards == {r.complaint_ward_name for r in cw}

    def test_known_hand_decisions_are_pinned(self, cw):
        """Regression guard on the calls string distance gets wrong."""
        assert cw.ward_no("Ulsoor") == 90              # Halasuru == Ulsoor
        assert cw.ward_no("Kempapura Agrahara") == 122
        assert cw.ward_no("Malleshwaram") == 45
        assert cw.ward_no("Someshwara") == 3           # via the 243-ward split
        assert cw.ward_no("Subedarapalya") == 65       # Kadu Malleshwar, by elimination

    def test_vijayanagar_and_vignana_nagar_stay_distinct(self, cw):
        assert cw.ward_no("Vijay Nagar") == 123
        assert cw.ward_no("Vignana Nagar") == 81


class TestNearestCell:
    def test_haversine_is_symmetric_and_zero_on_self(self):
        assert haversine_m(12.97, 77.59, 12.97, 77.59) == pytest.approx(0.0)
        a = haversine_m(12.97, 77.59, 13.10, 77.70)
        b = haversine_m(13.10, 77.70, 12.97, 77.59)
        assert a == pytest.approx(b)

    def test_haversine_matches_a_known_distance(self):
        # 0.1 degree of latitude is about 11.1 km anywhere.
        assert haversine_m(12.9, 77.6, 13.0, 77.6) == pytest.approx(11119, rel=0.01)

    def test_picks_the_closest_cell(self, cw):
        cells = [(1, 12.7716, 77.3946), (5, 12.9716, 77.5946), (9, 13.1716, 77.7946)]
        # Ulsoor sits near the city centre.
        assert cw.nearest_cell("Ulsoor", cells) == 5

    def test_no_cells_gives_none(self, cw):
        assert cw.nearest_cell("Ulsoor", []) is None


class TestExclusionRule:
    def test_nothing_is_excluded_now(self, cw):
        assert cw.excluded_names == set()
        assert cw.counts_by_method()["unresolved"] == 0

    def test_non_register_wards_are_kept(self, cw):
        """The 96 wards off the register are the Proof Two pool, not a gap."""
        names = sorted(cw.non_register_wards)
        keep, rep = apply_to_ward_series(pd.Series(names), cw)
        assert keep.all()
        assert rep["rows_excluded_unresolved"] == 0

    def test_unresolved_is_excluded_and_reported(self):
        c = WardCrosswalk([
            _m("Good", 1, "Good", "exact", ""),
            _m("Bad", None, None, "unresolved", "could not decide", lat=None, lon=None),
        ])
        s = pd.Series(["Good", "Good", "Bad", "Good"])
        keep, rep = apply_to_ward_series(s, c)
        assert list(keep) == [True, True, False, True]
        assert rep["rows_excluded_unresolved"] == 1
        assert rep["excluded_share_pct"] == pytest.approx(25.0)
        assert rep["excluded_ward_names"] == ["Bad"]

    def test_unknown_ward_raises_rather_than_guessing(self, cw):
        with pytest.raises(KeyError, match="absent from the crosswalk"):
            apply_to_ward_series(pd.Series(["Not A Real Ward"]), cw)

    def test_get_unknown_name_points_at_the_fix(self, cw):
        with pytest.raises(KeyError, match="do not fuzzy-match"):
            cw.get("Nowhere")

    def test_null_wards_are_dropped_and_counted(self, cw):
        s = pd.Series(["Ulsoor", None, "Ulsoor"])
        keep, rep = apply_to_ward_series(s, cw)
        assert list(keep) == [True, False, True]
        assert rep["rows_null_ward"] == 1


class TestValidation:
    def test_duplicate_name_rejected(self):
        with pytest.raises(ValueError, match="duplicate"):
            WardCrosswalk([_m("A", 1, "A"), _m("A", 2, "B")])

    def test_duplicate_ward_number_rejected(self):
        with pytest.raises(ValueError, match="claimed by both"):
            WardCrosswalk([_m("A", 5, "A"), _m("B", 5, "B")])

    def test_unknown_method_rejected(self):
        with pytest.raises(ValueError, match="unknown match_method"):
            WardCrosswalk([_m("A", 1, "A", "guessed")])

    def test_matched_row_without_number_rejected(self):
        with pytest.raises(ValueError, match="has no bbmp_ward_no"):
            WardCrosswalk([_m("A", None, None, "exact")])

    def test_ward_number_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="outside 1..198"):
            WardCrosswalk([_m("A", 250, "A", "exact")])

    def test_matched_row_without_centroid_rejected(self):
        with pytest.raises(ValueError, match="has no centroid"):
            WardCrosswalk([_m("A", 1, "A", "exact", lat=None, lon=None)])

    def test_unresolved_row_with_number_rejected(self):
        with pytest.raises(ValueError, match="carries a ward number"):
            WardCrosswalk([_m("A", 7, "A", "unresolved", "note")])

    def test_manual_row_without_note_rejected(self):
        with pytest.raises(ValueError, match="must carry a note"):
            WardCrosswalk([_m("A", 1, "A", "manual", "")])
