"""Monta estruturas de dados prontas para o Chart.js a partir de séries pandas."""

import pandas as pd


def _date_labels(index: pd.Index) -> list[str]:
    return [d.date().isoformat() if hasattr(d, "date") else str(d) for d in index]


def line_dataset(series: pd.Series, label: str) -> dict:
    return {
        "labels": _date_labels(series.index),
        "datasets": [{"label": label, "data": [None if pd.isna(v) else float(v) for v in series]}],
    }


def spread_zscore_chart(series: pd.DataFrame) -> dict:
    """Gráfico de z-score do spread com bandas em ±1 e ±2 desvios-padrão."""
    labels = _date_labels(series.index)
    zscore = [None if pd.isna(v) else float(v) for v in series["zscore"]]
    return {
        "labels": labels,
        "datasets": [
            {"label": "z-score do spread", "data": zscore, "band": False},
            {"label": "+2σ", "data": [2] * len(labels), "band": True},
            {"label": "+1σ", "data": [1] * len(labels), "band": True},
            {"label": "-1σ", "data": [-1] * len(labels), "band": True},
            {"label": "-2σ", "data": [-2] * len(labels), "band": True},
        ],
    }


def scatter_chart(series: pd.DataFrame, label_a: str, label_b: str) -> dict:
    points = [
        {"x": float(row.b), "y": float(row.a)} for row in series.itertuples() if pd.notna(row.a) and pd.notna(row.b)
    ]
    return {"label_a": label_a, "label_b": label_b, "points": points}


def rolling_correlation_chart(series: pd.DataFrame) -> dict:
    labels = _date_labels(series.index)
    values = [None if pd.isna(v) else float(v) for v in series["correlacao_movel"]]
    return {"labels": labels, "datasets": [{"label": "Correlação móvel", "data": values}]}


def rebased_multi_series_chart(series_by_label: dict[str, pd.Series]) -> dict:
    """Cada série é rebasada a 100 no seu primeiro valor disponível, para comparar variação
    percentual (não nível absoluto) entre séries de escalas diferentes (câmbio, índices)."""
    all_dates = sorted({d for series in series_by_label.values() for d in series.index})
    labels = _date_labels(pd.DatetimeIndex(all_dates))

    datasets = []
    for label, series in series_by_label.items():
        series = series.sort_index()
        if series.empty:
            continue
        base = float(series.iloc[0])
        rebased = (series / base) * 100 if base else series
        rebased = rebased.reindex(pd.DatetimeIndex(all_dates))
        datasets.append({"label": label, "data": [None if pd.isna(v) else float(v) for v in rebased]})

    return {"labels": labels, "datasets": datasets}
