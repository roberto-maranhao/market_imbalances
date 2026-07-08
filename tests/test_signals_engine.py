import datetime as dt

import numpy as np
import pandas as pd

from src.signals.engine import align_series, compute_pair_series, compute_pair_signal


def test_align_series_matches_monthly_to_nearest_prior_daily():
    daily_index = pd.date_range("2026-01-01", periods=90, freq="D")
    daily = pd.Series(np.arange(90, dtype=float), index=daily_index)

    monthly_index = pd.DatetimeIndex(["2026-01-15", "2026-02-15", "2026-03-15"])
    monthly = pd.Series([100.0, 200.0, 300.0], index=monthly_index)

    aligned = align_series(monthly, daily)

    assert list(aligned.index) == list(monthly_index)
    assert list(aligned["a"]) == [100.0, 200.0, 300.0]
    # dia 15/jan é o índice 14 da série diária (0-based, começando em 01/jan)
    assert aligned["b"].iloc[0] == 14.0


def test_align_series_drops_dates_outside_tolerance():
    a = pd.Series([1.0], index=pd.DatetimeIndex(["2026-01-01"]))
    b = pd.Series([2.0], index=pd.DatetimeIndex(["2026-06-01"]))  # bem fora da tolerância

    aligned = align_series(a, b, tolerance_days=35)

    assert aligned.empty


def test_compute_pair_signal_recovers_known_hedge_ratio():
    rng = np.random.default_rng(42)
    n = 120
    b_values = np.cumsum(rng.normal(0, 1, n)) + 100
    noise = rng.normal(0, 0.5, n)
    a_values = 2.0 * b_values + 10 + noise  # a deveria ser cointegrada com b, hedge_ratio ~= 2

    index = pd.date_range("2026-01-01", periods=n, freq="D")
    aligned = pd.DataFrame({"a": a_values, "b": b_values}, index=index)

    result = compute_pair_signal(aligned)

    assert result is not None
    assert result.n_obs == n
    assert result.data == dt.date(2026, 1, 1) + dt.timedelta(days=n - 1)
    assert abs(result.hedge_ratio - 2.0) < 0.2
    assert result.zscore is not None
    assert result.correlacao_movel is not None
    assert result.coint_pvalue is not None
    assert result.coint_pvalue < 0.10  # séries claramente cointegradas por construção


def test_compute_pair_signal_returns_none_below_min_obs():
    index = pd.date_range("2026-01-01", periods=5, freq="D")
    aligned = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [1, 2, 3, 4, 5]}, index=index)

    assert compute_pair_signal(aligned, min_obs=20) is None


def test_compute_pair_series_matches_signal_on_last_row():
    rng = np.random.default_rng(7)
    n = 80
    b_values = np.cumsum(rng.normal(0, 1, n)) + 50
    a_values = 1.5 * b_values + 5 + rng.normal(0, 0.3, n)
    index = pd.date_range("2026-01-01", periods=n, freq="D")
    aligned = pd.DataFrame({"a": a_values, "b": b_values}, index=index)

    series = compute_pair_series(aligned, corr_window=10)
    signal = compute_pair_signal(aligned, corr_window=10)

    assert len(series) == n
    assert list(series.columns) == ["a", "b", "spread", "zscore", "correlacao_movel", "hedge_ratio", "intercept"]
    assert signal is not None
    assert series["spread"].iloc[-1] == signal.spread
    assert series["zscore"].iloc[-1] == signal.zscore
    assert series["hedge_ratio"].iloc[-1] == signal.hedge_ratio
