import logging

import yfinance as yf

from src.collectors.types import PriceRecord

logger = logging.getLogger(__name__)

FONTE = "yfinance"


def _download(tickers: list[str], period: str, interval: str = "1d"):
    return yf.download(
        tickers,
        period=period,
        interval=interval,
        group_by="ticker",
        progress=False,
        auto_adjust=True,
        threads=True,
    )


def _close_series(data, ticker: str, is_single: bool):
    series = data["Close"] if is_single else data[ticker]["Close"]
    return series.dropna()


def fetch_latest(tickers: list[str]) -> list[PriceRecord]:
    """Último fechamento disponível para cada ticker. yfinance não é API oficial —
    trata-se como best-effort: tickers que falharem são pulados, não derrubam o job."""
    if not tickers:
        return []

    try:
        data = _download(tickers, period="5d")
    except Exception:
        logger.exception("yfinance: falha ao baixar %s", tickers)
        return []

    is_single = len(tickers) == 1
    records: list[PriceRecord] = []
    for ticker in tickers:
        try:
            series = _close_series(data, ticker, is_single)
            if series.empty:
                logger.warning("yfinance: sem dados para %s", ticker)
                continue
            records.append(
                PriceRecord(ticker=ticker, data=series.index[-1].date(), preco=float(series.iloc[-1]), fonte=FONTE)
            )
        except Exception:
            logger.exception("yfinance: falha ao processar %s", ticker)

    return records


def fetch_history(tickers: list[str], period: str = "2y") -> list[PriceRecord]:
    """Série histórica completa (não só o último fechamento) — usada para popular
    dados suficientes para cointegração/z-score/correlação móvel (ver src/signals)."""
    if not tickers:
        return []

    try:
        data = _download(tickers, period=period)
    except Exception:
        logger.exception("yfinance: falha ao baixar histórico de %s", tickers)
        return []

    is_single = len(tickers) == 1
    records: list[PriceRecord] = []
    for ticker in tickers:
        try:
            series = _close_series(data, ticker, is_single)
            if series.empty:
                logger.warning("yfinance: sem histórico para %s", ticker)
                continue
            for index, price in series.items():
                records.append(PriceRecord(ticker=ticker, data=index.date(), preco=float(price), fonte=FONTE))
        except Exception:
            logger.exception("yfinance: falha ao processar histórico de %s", ticker)

    return records
