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


@dataclass(frozen=True)
class PairSignal:
    data: dt.date
    hedge_ratio: float
    spread: float
    zscore: float | None
    correlacao_movel: float | None
    coint_pvalue: float | None
    n_obs: int


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


def _zscore_latest(spread: np.ndarray) -> float | None:
    if len(spread) < 2:
        return None
    std = spread.std(ddof=1)
    if not std or np.isnan(std):
        return None
    return float((spread[-1] - spread.mean()) / std)


def _rolling_correlation_latest(a: pd.Series, b: pd.Series, window: int) -> float | None:
    if len(a) < window:
        return None
    corr = a.tail(window).corr(b.tail(window))
    return float(corr) if pd.notna(corr) else None


def compute_pair_signal(
    aligned: pd.DataFrame,
    corr_window: int = DEFAULT_CORR_WINDOW,
    min_obs: int = MIN_OBS,
) -> PairSignal | None:
    """Recebe um DataFrame com colunas 'a' e 'b' (índice = data, já alinhado) e devolve o
    sinal do dia mais recente, ou None se não houver observações suficientes."""
    if len(aligned) < min_obs:
        return None

    a, b = aligned["a"], aligned["b"]

    X = sm.add_constant(b.to_numpy())
    model = sm.OLS(a.to_numpy(), X).fit()
    hedge_ratio = float(model.params[1])
    spread = np.asarray(model.resid)

    try:
        _, coint_pvalue, _ = coint(a.to_numpy(), b.to_numpy())
        coint_pvalue = float(coint_pvalue)
    except Exception:
        coint_pvalue = None

    latest_index = aligned.index[-1]
    latest_date = latest_index.date() if hasattr(latest_index, "date") else latest_index

    return PairSignal(
        data=latest_date,
        hedge_ratio=hedge_ratio,
        spread=float(spread[-1]),
        zscore=_zscore_latest(spread),
        correlacao_movel=_rolling_correlation_latest(a, b, corr_window),
        coint_pvalue=coint_pvalue,
        n_obs=len(aligned),
    )
