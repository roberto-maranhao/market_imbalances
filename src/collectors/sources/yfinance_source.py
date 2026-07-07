import logging

import yfinance as yf

from src.collectors.types import PriceRecord

logger = logging.getLogger(__name__)

FONTE = "yfinance"


def fetch_latest(tickers: list[str]) -> list[PriceRecord]:
    """Último fechamento disponível para cada ticker. yfinance não é API oficial —
    trata-se como best-effort: tickers que falharem são pulados, não derrubam o job."""
    if not tickers:
        return []

    records: list[PriceRecord] = []
    try:
        data = yf.download(
            tickers,
            period="5d",
            interval="1d",
            group_by="ticker",
            progress=False,
            auto_adjust=True,
            threads=True,
        )
    except Exception:
        logger.exception("yfinance: falha ao baixar %s", tickers)
        return []

    is_single = len(tickers) == 1
    for ticker in tickers:
        try:
            series = data["Close"] if is_single else data[ticker]["Close"]
            series = series.dropna()
            if series.empty:
                logger.warning("yfinance: sem dados para %s", ticker)
                continue
            last_date = series.index[-1].date()
            last_price = float(series.iloc[-1])
            records.append(PriceRecord(ticker=ticker, data=last_date, preco=last_price, fonte=FONTE))
        except Exception:
            logger.exception("yfinance: falha ao processar %s", ticker)

    return records
