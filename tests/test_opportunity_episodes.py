import datetime as dt

import pandas as pd

from src.signals.engine import detect_opportunity_episodes


def make_series(zscores: list[float], a: list[float], b: list[float]) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=len(zscores), freq="D")
    return pd.DataFrame({"a": a, "b": b, "zscore": zscores}, index=index)


def test_detects_a_single_closed_episode():
    # dias 0-1: normal | dia 2: abre (z=2.5) | dia 3: pico (z=3.0) | dia 4: fecha (z=0.4)
    zscores = [0.1, 0.3, 2.5, 3.0, 0.4]
    a = [10, 10, 12, 13, 10.5]
    b = [10, 10, 10, 10, 10]

    episodes = detect_opportunity_episodes(make_series(zscores, a, b))

    assert len(episodes) == 1
    ep = episodes[0]
    assert ep.inicio == dt.date(2026, 1, 3)
    assert ep.fim == dt.date(2026, 1, 5)
    assert ep.pico_zscore == 3.0
    assert ep.a_inicio == 12
    assert ep.a_fim == 10.5
    assert ep.duracao_dias == 2


def test_open_episode_has_no_end_date_but_has_current_values():
    zscores = [0.1, 2.2, 2.8]  # abre e nunca fecha
    a = [10, 12, 13]
    b = [10, 10, 10]

    episodes = detect_opportunity_episodes(make_series(zscores, a, b))

    assert len(episodes) == 1
    ep = episodes[0]
    assert ep.fim is None
    assert ep.a_fim == 13  # último valor observado, mesmo sem ter "fechado"
    assert ep.pico_zscore == 2.8


def test_multiple_episodes_returned_most_recent_first():
    # episódio 1: dias 1-2 (abre/fecha) | episódio 2: dias 4-5 (abre/fecha)
    zscores = [0.1, 2.1, 0.2, 0.1, -2.3, -0.1]
    a = [10] * 6
    b = [10] * 6

    episodes = detect_opportunity_episodes(make_series(zscores, a, b))

    assert len(episodes) == 2
    assert episodes[0].inicio == dt.date(2026, 1, 5)  # mais recente primeiro
    assert episodes[1].inicio == dt.date(2026, 1, 2)
    assert episodes[0].pico_zscore == -2.3


def test_no_episode_when_zscore_never_crosses_threshold():
    zscores = [0.1, -0.5, 1.0, -1.5, 0.9]
    a = [10] * 5
    b = [10] * 5

    episodes = detect_opportunity_episodes(make_series(zscores, a, b))

    assert episodes == []


def test_ignores_nan_zscores():
    zscores = [float("nan"), float("nan"), 2.5, 0.1]
    a = [10, 10, 12, 10.5]
    b = [10, 10, 10, 10]

    episodes = detect_opportunity_episodes(make_series(zscores, a, b))

    assert len(episodes) == 1
    assert episodes[0].inicio == dt.date(2026, 1, 3)
