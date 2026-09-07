"""Tests for the daily weather aggregation.

The leakage tests are the point of this file. `rain_percentile` and
`return_period_yrs` are the two columns that can silently invalidate every
downstream result (CLAUDE.md rule 1), and the failure is invisible — the
numbers look perfectly reasonable either way. So they are pinned here.
"""
from datetime import date

import numpy as np
import pytest

from app.ingestion.weather_daily import (
    _expanding_percentile, _expanding_return_period, _season_position,
)


class TestExpandingPercentileDoesNotLeak:
    def test_ignores_the_future_entirely(self):
        """A huge value at the end must not change any earlier percentile."""
        base = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        spiked = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 9999.0])
        a = _expanding_percentile(base, min_history=2)
        b = _expanding_percentile(spiked, min_history=2)
        np.testing.assert_array_equal(a[:5], b[:5])

    def test_uses_strictly_prior_days(self):
        """Day i's percentile is computed over days [0, i), never including i."""
        v = np.array([10.0, 10.0, 10.0, 0.0])
        out = _expanding_percentile(v, min_history=1)
        # index 1: prior=[10]; 10 <= 10 -> 1/1
        assert out[1] == pytest.approx(1.0)
        # index 3: prior=[10,10,10]; none <= 0 -> 0/3
        assert out[3] == pytest.approx(0.0)

    def test_below_min_history_is_nan_not_a_guess(self):
        v = np.arange(10, dtype=float)
        out = _expanding_percentile(v, min_history=5)
        assert np.isnan(out[:5]).all()
        assert not np.isnan(out[5:]).any()

    def test_percentile_stays_in_unit_interval(self):
        rng = np.random.default_rng(0)
        out = _expanding_percentile(rng.gamma(0.4, 8.0, 500), min_history=30)
        finite = out[~np.isnan(out)]
        assert finite.min() >= 0.0 and finite.max() <= 1.0

    def test_prefix_stability(self):
        """Truncating the series must not change the surviving values.

        This is the property that actually matters: recomputing on a longer
        history later must reproduce what was written at the time.
        """
        rng = np.random.default_rng(7)
        v = rng.gamma(0.4, 8.0, 300)
        full = _expanding_percentile(v, min_history=30)
        part = _expanding_percentile(v[:200], min_history=30)
        np.testing.assert_allclose(full[:200], part, equal_nan=True)


class TestExpandingReturnPeriod:
    def test_ignores_the_future(self):
        base = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        spiked = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 9999.0])
        a = _expanding_return_period(base, min_history=2)
        b = _expanding_return_period(spiked, min_history=2)
        np.testing.assert_array_equal(a[:5], b[:5])

    def test_unprecedented_value_is_finite(self):
        v = np.array([1.0, 1.0, 1.0, 1.0, 500.0])
        out = _expanding_return_period(v, min_history=2)
        assert np.isfinite(out[4]) and out[4] > 0

    def test_a_common_value_returns_a_short_period(self):
        v = np.full(400, 5.0)
        out = _expanding_return_period(v, min_history=30)
        assert out[-1] < 0.02  # every single day qualifies -> ~1/365 yr

    def test_bigger_rain_means_longer_return_period(self):
        rng = np.random.default_rng(3)
        v = np.append(rng.gamma(0.4, 5.0, 400), [1.0, 300.0])
        out = _expanding_return_period(v, min_history=100)
        assert out[-1] > out[-2]


class TestSeasonPosition:
    def test_counts_days_into_a_normal_season(self):
        # Bengaluru: April-November
        assert _season_position(date(2024, 4, 1), 4, 11) == 0
        assert _season_position(date(2024, 4, 15), 4, 11) == 14

    def test_none_outside_the_season(self):
        assert _season_position(date(2024, 1, 15), 4, 11) is None
        assert _season_position(date(2024, 12, 15), 4, 11) is None

    def test_handles_a_season_wrapping_the_new_year(self):
        # A southern-hemisphere-style Nov-Feb season.
        assert _season_position(date(2024, 11, 1), 11, 2) == 0
        jan = _season_position(date(2025, 1, 10), 11, 2)
        assert jan is not None and jan > 60
        assert _season_position(date(2024, 6, 1), 11, 2) is None
