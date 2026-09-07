"""Tests for the ward crosswalk artifact and its loader-side rule.

The committed CSV is checked as data, not just the code that reads it — the
artifact is the deliverable, and a hand-edited CSV is exactly the kind of file
that drifts silently.
"""
import csv

import pandas as pd
import pytest

from app.ingestion.ward_crosswalk import (
    CROSSWALK_PATH, VALID_METHODS, WardCrosswalk, WardMapping,
    apply_to_ward_series, load_crosswalk,
)


@pytest.fixture(scope="module")
def cw():
    return load_crosswalk()


def _m(name, no=None, rname=None, method="not_in_register", notes="n"):
    return WardMapping(name, no, rname, method, notes)


class TestCommittedArtifact:
    def test_file_exists_and_loads(self, cw):
        assert len(cw) == 198

    def test_every_complaint_ward_appears_exactly_once(self):
        with CROSSWALK_PATH.open(newline="", encoding="utf-8") as fh:
            names = [r["complaint_ward_name"] for r in csv.DictReader(fh)]
        assert len(names) == 198
        assert len(set(names)) == 198

    def test_matches_the_ward_names_actually_in_the_csvs(self, cw):
        """The artifact must cover the live data, not a stale snapshot of it."""
        import pathlib
        raw = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
        files = sorted(raw.glob("bbmp_grievances_*.csv"))
        if not files:
            pytest.skip("raw grievance CSVs not present (they are gitignored)")
        seen = set()
        for f in files:
            s = pd.read_csv(f, dtype=str, usecols=["Ward Name"],
                            keep_default_na=False, na_values=["", "NON Ward"])
            seen |= set(s["Ward Name"].dropna().unique())
        missing = seen - {n for n in cw._by_name}
        assert not missing, f"ward names in the data but not the crosswalk: {sorted(missing)}"

    def test_all_methods_are_valid(self, cw):
        assert set(cw.counts_by_method()) <= VALID_METHODS

    def test_no_register_ward_claimed_twice(self, cw):
        nos = [r.register_ward_no for r in cw._by_name.values() if r.has_ward_no]
        assert len(nos) == len(set(nos))

    def test_ward_numbers_are_in_bbmp_range(self, cw):
        for r in cw._by_name.values():
            if r.has_ward_no:
                assert 1 <= r.register_ward_no <= 198

    def test_manual_rows_all_carry_a_note(self, cw):
        for r in cw._by_name.values():
            if r.match_method == "manual":
                assert len(r.notes) > 20, f"{r.complaint_ward_name} has a thin note"

    def test_rows_without_a_number_are_not_silently_mapped(self, cw):
        for r in cw._by_name.values():
            if r.match_method in {"not_in_register", "unresolved"}:
                assert r.register_ward_no is None
                assert not r.register_ward_name

    def test_known_hand_decisions_are_pinned(self, cw):
        """Regression guard on the three that string distance gets wrong."""
        assert cw.ward_no("Ulsoor") == 90                 # Halasuru == Ulsoor
        assert cw.ward_no("Kempapura Agrahara") == 122
        assert cw.ward_no("Malleshwaram") is not None
        # Malleshwaram must NOT have been given Kadu Malleshwar's ward 65.
        assert cw.ward_no("Malleshwaram") != 65
        assert 65 not in {r.register_ward_no for r in cw._by_name.values()}

    def test_vijayanagar_and_vignana_nagar_stay_distinct(self, cw):
        assert cw.ward_no("Vijay Nagar") == 123
        assert cw.ward_no("Vignana Nagar") == 81


class TestExclusionRule:
    def test_not_in_register_is_kept_not_excluded(self, cw):
        """The 96 wards absent from the register must stay in the panel."""
        not_in_reg = [n for n, r in cw._by_name.items()
                      if r.match_method == "not_in_register"]
        assert len(not_in_reg) > 50
        keep, rep = apply_to_ward_series(pd.Series(not_in_reg), cw)
        assert keep.all()
        assert rep["rows_excluded_unresolved"] == 0

    def test_unresolved_is_excluded_and_reported(self):
        c = WardCrosswalk([
            _m("Good", 1, "Good", "exact", ""),
            _m("Bad", None, None, "unresolved", "could not decide"),
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
            WardCrosswalk([_m("A", 1, "A", "exact"), _m("A", 2, "B", "exact")])

    def test_duplicate_ward_number_rejected(self):
        with pytest.raises(ValueError, match="claimed by both"):
            WardCrosswalk([_m("A", 5, "A", "exact"), _m("B", 5, "B", "exact")])

    def test_unknown_method_rejected(self):
        with pytest.raises(ValueError, match="unknown match_method"):
            WardCrosswalk([_m("A", 1, "A", "guessed")])

    def test_matched_row_without_number_rejected(self):
        with pytest.raises(ValueError, match="has no register_ward_no"):
            WardCrosswalk([_m("A", None, None, "exact")])

    def test_unmatched_row_with_number_rejected(self):
        with pytest.raises(ValueError, match="carries a register_ward_no"):
            WardCrosswalk([_m("A", 7, "A", "unresolved", "note")])

    def test_manual_row_without_note_rejected(self):
        with pytest.raises(ValueError, match="must carry a note"):
            WardCrosswalk([_m("A", 1, "A", "manual", "")])
