"""Model selection for the Open-Meteo archive loader.

The model choice is load-bearing: ERA5 resolves BBMP into 3 cells and
ECMWF-IFS into 14 (profile §17.1). A silent fallback to the coarse model
would quietly undo that, so the default and the cell list are pinned.
"""
import math

import pytest

from app.ingestion.open_meteo import (
    DEFAULT_MODEL, IFS_CELLS, MODELS, source_for,
)
from app.ingestion.ward_crosswalk import haversine_m, load_crosswalk


class TestModelRegistry:
    def test_default_is_the_finer_model(self):
        assert DEFAULT_MODEL == "ecmwf_ifs"

    def test_every_model_has_a_distinct_source_name(self):
        names = [source_for(m)[0] for m in MODELS]
        assert len(names) == len(set(names))

    def test_source_carries_the_model_description(self):
        name, kw = source_for("ecmwf_ifs")
        assert "IFS" in name
        assert "9 km" in kw["description"]
        assert kw["url"].startswith("https://")

    def test_era5_land_is_registered_but_flagged_unusable(self):
        """It has a fine grid but Open-Meteo returns NULL precipitation."""
        _, kw = source_for("era5_land")
        assert "NULL" in kw["description"]

    def test_unknown_model_raises(self):
        with pytest.raises(ValueError, match="unknown model"):
            source_for("gfs")


class TestIfsCells:
    def test_there_are_fourteen(self):
        assert len(IFS_CELLS) == 14

    def test_all_distinct(self):
        assert len(set(IFS_CELLS)) == 14

    def test_all_inside_the_bengaluru_box(self):
        for lat, lon in IFS_CELLS:
            assert 12.7 < lat < 13.3, (lat, lon)
            assert 77.3 < lon < 77.9, (lat, lon)

    def test_spacing_is_finer_than_era5(self):
        """The whole point: IFS steps ~8 km where ERA5 steps ~28 km."""
        lats = sorted({round(a, 5) for a, _ in IFS_CELLS})
        steps = [b - a for a, b in zip(lats, lats[1:])]
        assert min(steps) < 0.09, steps
        assert 111.32 * min(steps) < 10.0  # km

    def test_every_ward_has_a_cell_within_ten_km(self):
        """No ward should be stranded far from its assigned cell."""
        cw = load_crosswalk()
        worst = 0.0
        for m in cw:
            d = min(haversine_m(m.centroid_lat, m.centroid_lon, la, lo)
                    for la, lo in IFS_CELLS)
            worst = max(worst, d)
        assert worst < 10_000, f"worst ward-to-cell distance {worst:.0f} m"

    def test_wards_spread_across_most_cells(self):
        """Regression guard on the finding that motivated the switch: under
        ERA5 one cell held 89% of wards. Under IFS no cell may hold half."""
        cw = load_crosswalk()
        counts = {}
        for m in cw:
            best = min(IFS_CELLS,
                       key=lambda c: haversine_m(m.centroid_lat, m.centroid_lon, *c))
            counts[best] = counts.get(best, 0) + 1
        assert len(counts) >= 12, f"only {len(counts)} cells used"
        assert max(counts.values()) / len(cw) < 0.40, counts
