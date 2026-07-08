"""Motor de sinais: cointegração, hedge ratio, spread/z-score e correlação móvel entre
duas séries de preços (ver plan.json -> theory.statistical_methods)."""

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint

MIN_OBS = 20  # abaixo disso, cointegração/z-score não são estatisticamente confiáveis
DEFAULT_CORR_WINDOW = 30
DEFAULT_ALIGN_TOLERANCE_DAYS = 35  # cobre o pior caso: série mensal (BCB) vs diária


DEFAULT_ENTER_THRESHOLD = 2.0  # |zscore| a partir do qual uma oportunidade é considerada "aberta"
DEFAULT_EXIT_THRESHOLD = 0.5  # |zscore| abaixo do qual o spread é considerado "normalizado"


@dataclass(frozen=True)
class PairSignal:
    data: dt.date
    hedge_ratio: float
    spread: float
    zscore: float | None
    correlacao_movel: float | None
    coint_pvalue: float | None
    n_obs: int


@dataclass(frozen=True)
class OpportunityEpisode:
    """Um período em que o spread se afastou da média (|zscore| >= enter_threshold) até
    voltar a se normalizar (|zscore| <= exit_threshold) — ou, se ainda não normalizou, o
    trecho aberto até a última data disponível (fim=None)."""

    inicio: dt.date
    fim: dt.date | None  # None = ainda aberta na última data da série
    pico_zscore: float
    a_inicio: float
    a_fim: float
    b_inicio: float
    b_fim: float
    duracao_dias: int


def align_series(
    series_a: pd.Series, series_b: pd.Series, tolerance_days: int = DEFAULT_ALIGN_TOLERANCE_DAYS
) -> pd.DataFrame:
    """Alinha duas séries indexadas por data que podem ter frequências diferentes (ex:
    câmbio diário vs índice mensal do BCB). A série mais esparsa vira a âncora; para cada
    data-âncora, busca o valor mais recente disponível na outra série dentro da tolerância
    (merge_asof, direção 'backward' — nunca olha para o futuro)."""
    a = series_a.sort_index()
    b = series_b.sort_index()
    a_df = pd.DataFrame({"data": pd.DatetimeIndex(a.index), "a": a.values})
    b_df = pd.DataFrame({"data": pd.DatetimeIndex(b.index), "b": b.values})

    if len(a_df) <= len(b_df):
        left, right = a_df, b_df
    else:
        left, right = b_df, a_df

    merged = pd.merge_asof(
        left.sort_values("data"),
        right.sort_values("data"),
        on="data",
        direction="backward",
        tolerance=pd.Timedelta(days=tolerance_days),
    )
    merged = merged.dropna(subset=["a", "b"]).set_index("data")
    return merged[["a", "b"]]


def compute_pair_series(aligned: pd.DataFrame, corr_window: int = DEFAULT_CORR_WINDOW) -> pd.DataFrame:
    """Recebe um DataFrame com colunas 'a'/'b' (já alinhadas) e devolve, para CADA data,
    o spread (resíduo da regressão a ~ b), o z-score do spread contra a amostra inteira, e a
    correlação móvel — usado tanto para o sinal do dia quanto para os gráficos históricos do
    dashboard (Fase 3)."""
    a, b = aligned["a"], aligned["b"]

    X = sm.add_constant(b.to_numpy())
    model = sm.OLS(a.to_numpy(), X).fit()
    intercept = float(model.params[0])
    hedge_ratio = float(model.params[1])
    spread = pd.Series(np.asarray(model.resid), index=aligned.index)

    std = spread.std(ddof=1)
    zscore = (spread - spread.mean()) / std if std and not np.isnan(std) else pd.Series(np.nan, index=spread.index)

    rolling_corr = a.rolling(corr_window).corr(b)

    return pd.DataFrame(
        {
            "a": a,
            "b": b,
            "spread": spread,
            "zscore": zscore,
            "correlacao_movel": rolling_corr,
            "hedge_ratio": hedge_ratio,
            "intercept": intercept,
        },
        index=aligned.index,
    )


def compute_pair_signal(
    aligned: pd.DataFrame,
    corr_window: int = DEFAULT_CORR_WINDOW,
    min_obs: int = MIN_OBS,
) -> PairSignal | None:
    """Recebe um DataFrame com colunas 'a' e 'b' (índice = data, já alinhado) e devolve o
    sinal do dia mais recente, ou None se não houver observações suficientes."""
    if len(aligned) < min_obs:
        return None

    series = compute_pair_series(aligned, corr_window=corr_window)
    last = series.iloc[-1]

    try:
        _, coint_pvalue, _ = coint(aligned["a"].to_numpy(), aligned["b"].to_numpy())
        coint_pvalue = float(coint_pvalue)
    except Exception:
        coint_pvalue = None

    latest_index = aligned.index[-1]
    latest_date = latest_index.date() if hasattr(latest_index, "date") else latest_index
    zscore = float(last["zscore"]) if pd.notna(last["zscore"]) else None
    correlacao_movel = float(last["correlacao_movel"]) if pd.notna(last["correlacao_movel"]) else None

    return PairSignal(
        data=latest_date,
        hedge_ratio=float(last["hedge_ratio"]),
        spread=float(last["spread"]),
        zscore=zscore,
        correlacao_movel=correlacao_movel,
        coint_pvalue=coint_pvalue,
        n_obs=len(aligned),
    )


def _as_date(index_value) -> dt.date:
    return index_value.date() if hasattr(index_value, "date") else index_value


def _build_episode(series: pd.DataFrame, start_idx, end_idx, peak_zscore: float, still_open: bool) -> OpportunityEpisode:
    return OpportunityEpisode(
        inicio=_as_date(start_idx),
        fim=None if still_open else _as_date(end_idx),
        pico_zscore=float(peak_zscore),
        a_inicio=float(series.loc[start_idx, "a"]),
        a_fim=float(series.loc[end_idx, "a"]),
        b_inicio=float(series.loc[start_idx, "b"]),
        b_fim=float(series.loc[end_idx, "b"]),
        duracao_dias=(end_idx - start_idx).days,
    )


def detect_opportunity_episodes(
    series: pd.DataFrame,
    enter_threshold: float = DEFAULT_ENTER_THRESHOLD,
    exit_threshold: float = DEFAULT_EXIT_THRESHOLD,
) -> list[OpportunityEpisode]:
    """Varre a série de z-score (coluna 'zscore' de compute_pair_series) e monta a lista de
    episódios históricos em que o spread se esticou além de enter_threshold desvios-padrão e
    depois voltou para dentro de exit_threshold. Mais recente primeiro. Se o último ponto da
    série ainda estiver com |zscore| >= enter_threshold, o episódio aparece com fim=None
    ('em andamento') e os valores 'fim' refletem a última observação disponível."""
    episodes: list[OpportunityEpisode] = []
    in_episode = False
    start_idx = None
    peak_zscore = 0.0

    for idx, zscore in series["zscore"].items():
        if pd.isna(zscore):
            continue
        if not in_episode:
            if abs(zscore) >= enter_threshold:
                in_episode = True
                start_idx = idx
                peak_zscore = zscore
        else:
            if abs(zscore) > abs(peak_zscore):
                peak_zscore = zscore
            if abs(zscore) <= exit_threshold:
                episodes.append(_build_episode(series, start_idx, idx, peak_zscore, still_open=False))
                in_episode = False
                start_idx = None
                peak_zscore = 0.0

    if in_episode:
        episodes.append(_build_episode(series, start_idx, series.index[-1], peak_zscore, still_open=True))

    episodes.reverse()
    return episodes
