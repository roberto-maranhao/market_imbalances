"""Dados para o case study SpaceX/bolha de IA (ver plan.json -> case_studies.spacex_ai_bubble)."""

import pandas as pd
from sqlalchemy.orm import Session

from src.collectors.sources.edgar_source import CIKS
from src.models import Instrument
from src.signals.loader import load_price_series

THERMOMETER_TICKERS = ["SMH", "NVDA", "CRWV", "DLR", "EQIX", "SPCX", "RKLB"]


def load_hyperscaler_series(session: Session) -> dict[str, dict[str, pd.Series]]:
    """Para cada hyperscaler monitorado, retorna a série trimestral de capex e receita
    (pode faltar um dos dois, ou trimestres específicos — ver risks_and_caveats do plan.json:
    granularidade varia por empresa, ex: Oracle não reporta capex por trimestre)."""
    result: dict[str, dict[str, pd.Series]] = {}
    for ticker in CIKS:
        series = {}
        for metric, key in [("CAPEX", "capex"), ("REVENUE", "revenue")]:
            instrument = session.query(Instrument).filter_by(ticker=f"{ticker}_{metric}").one_or_none()
            if instrument is not None:
                s = load_price_series(session, instrument)
                if not s.empty:
                    series[key] = s
        if series:
            result[ticker] = series
    return result


def capex_intensity_index(hyperscaler_series: dict[str, dict[str, pd.Series]]) -> pd.Series:
    """Para cada trimestre em que pelo menos uma empresa tem capex E receita, soma capex e
    soma receita entre as empresas com dado naquele trimestre, e devolve a razão agregada.
    O conjunto de empresas contribuindo pode variar de trimestre a trimestre — é uma
    simplificação documentada no plan.json, não um artefato escondido."""
    capex_by_quarter: dict[pd.Timestamp, float] = {}
    revenue_by_quarter: dict[pd.Timestamp, float] = {}

    for series in hyperscaler_series.values():
        capex, revenue = series.get("capex"), series.get("revenue")
        if capex is None or revenue is None:
            continue
        common_dates = capex.index.intersection(revenue.index)
        for date in common_dates:
            capex_by_quarter[date] = capex_by_quarter.get(date, 0.0) + float(capex.loc[date])
            revenue_by_quarter[date] = revenue_by_quarter.get(date, 0.0) + float(revenue.loc[date])

    dates = sorted(capex_by_quarter)
    if not dates:
        return pd.Series(dtype=float)
    ratios = [capex_by_quarter[d] / revenue_by_quarter[d] for d in dates if revenue_by_quarter[d]]
    valid_dates = [d for d in dates if revenue_by_quarter[d]]
    return pd.Series(ratios, index=pd.DatetimeIndex(valid_dates))


def thermometer_basket_index(session: Session, tickers: list[str] = THERMOMETER_TICKERS) -> pd.Series:
    """Cesta igualmente ponderada dos ativos 'termômetro' (ver plan.json), cada um rebasado
    a 100 no seu primeiro valor disponível e depois calculada a média simples — mede retorno
    acumulado comparável entre ativos de preço/histórico bem diferentes (ex: SPCX só tem
    poucas semanas de histórico pós-IPO, os demais têm anos)."""
    rebased_series = []
    for ticker in tickers:
        instrument = session.query(Instrument).filter_by(ticker=ticker).one_or_none()
        if instrument is None:
            continue
        series = load_price_series(session, instrument)
        if series.empty:
            continue
        rebased_series.append((series / float(series.iloc[0])) * 100)

    if not rebased_series:
        return pd.Series(dtype=float)

    combined = pd.concat(rebased_series, axis=1)
    return combined.mean(axis=1, skipna=True)


def latest_snapshot_table(hyperscaler_series: dict[str, dict[str, pd.Series]]) -> list[dict]:
    """Mostra o capex e a receita mais recentes de cada empresa (podem ser de trimestres
    diferentes entre si). A razão capex/receita só é calculada no último trimestre em que
    AMBAS as séries têm dado (evita dividir capex de um trimestre pela receita de outro)."""
    rows = []
    for ticker, series in sorted(hyperscaler_series.items()):
        capex, revenue = series.get("capex"), series.get("revenue")

        ratio = None
        ratio_data = None
        if capex is not None and revenue is not None:
            common = capex.index.intersection(revenue.index)
            if len(common) > 0:
                last_common = common.max()
                revenue_val = float(revenue.loc[last_common])
                if revenue_val:
                    ratio = float(capex.loc[last_common]) / revenue_val
                    ratio_data = last_common.date()

        rows.append(
            {
                "ticker": ticker,
                "capex_data": capex.index[-1].date() if capex is not None and not capex.empty else None,
                "capex": float(capex.iloc[-1]) if capex is not None and not capex.empty else None,
                "revenue_data": revenue.index[-1].date() if revenue is not None and not revenue.empty else None,
                "revenue": float(revenue.iloc[-1]) if revenue is not None and not revenue.empty else None,
                "ratio": ratio,
                "ratio_data": ratio_data,
            }
        )
    return rows
