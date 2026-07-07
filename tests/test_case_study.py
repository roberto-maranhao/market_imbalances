import datetime as dt

import pandas as pd

from src.web.case_study import capex_intensity_index, latest_snapshot_table


def series(pairs: list[tuple[str, float]]) -> pd.Series:
    dates = pd.DatetimeIndex([d for d, _ in pairs])
    return pd.Series([v for _, v in pairs], index=dates)


def test_capex_intensity_index_aggregates_only_matching_quarters():
    hyperscaler_series = {
        "MSFT": {
            "capex": series([("2026-03-31", 30.0), ("2026-06-30", 35.0)]),
            "revenue": series([("2026-03-31", 80.0), ("2026-06-30", 90.0)]),
        },
        "NVDA": {
            "capex": series([("2026-03-31", 2.0)]),
            "revenue": series([("2026-03-31", 80.0)]),
        },
        "ORCL": {
            # só capex, sem receita nesse trimestre -> não deve contribuir
            "capex": series([("2026-03-31", 5.0)]),
        },
    }

    result = capex_intensity_index(hyperscaler_series)

    assert list(result.index) == [pd.Timestamp("2026-03-31"), pd.Timestamp("2026-06-30")]
    # 2026-03-31: (30+2)/(80+80) = 32/160 = 0.2
    assert result.iloc[0] == 0.2
    # 2026-06-30: só MSFT tem dado nesse trimestre -> 35/90
    assert abs(result.iloc[1] - (35.0 / 90.0)) < 1e-9


def test_capex_intensity_index_empty_when_no_overlap():
    hyperscaler_series = {
        "MSFT": {"capex": series([("2026-03-31", 30.0)])},  # sem receita
    }

    result = capex_intensity_index(hyperscaler_series)

    assert result.empty


def test_latest_snapshot_table_uses_last_common_quarter_for_ratio():
    hyperscaler_series = {
        "MSFT": {
            "capex": series([("2026-03-31", 30.0), ("2026-06-30", 35.0)]),  # capex mais novo que a receita
            "revenue": series([("2026-03-31", 80.0)]),
        },
    }

    rows = latest_snapshot_table(hyperscaler_series)

    assert len(rows) == 1
    row = rows[0]
    assert row["ticker"] == "MSFT"
    assert row["capex"] == 35.0
    assert row["capex_data"] == dt.date(2026, 6, 30)
    assert row["revenue"] == 80.0
    # razão usa o último trimestre em comum (2026-03-31), não o capex mais recente (Q2)
    assert row["ratio"] == 30.0 / 80.0
    assert row["ratio_data"] == dt.date(2026, 3, 31)
