import datetime as dt
import logging

from src.collectors.http import get_with_retry
from src.collectors.types import PriceRecord
from src.config import BRAPI_TOKEN

logger = logging.getLogger(__name__)

FONTE = "brapi.dev"
BASE_URL = "https://brapi.dev/api/quote/{tickers}"


def fetch_latest(tickers: list[str]) -> list[PriceRecord]:
    """tickers sem sufixo .SA (ex: 'VALE3', 'PETR4'). Sem BRAPI_TOKEN, só funciona
    para os 4 tickers de teste da API (PETR4, VALE3, MGLU3, ITUB4)."""
    if not tickers:
        return []

    url = BASE_URL.format(tickers=",".join(tickers))
    params = {"token": BRAPI_TOKEN} if BRAPI_TOKEN else {}

    try:
        resp = get_with_retry(url, params=params)
    except Exception:
        logger.exception("brapi.dev: falha ao buscar %s", tickers)
        return []

    payload = resp.json()
    records: list[PriceRecord] = []
    for item in payload.get("results", []):
        symbol = item.get("symbol")
        price = item.get("regularMarketPrice")
        if symbol is None or price is None:
            continue
        market_time = item.get("regularMarketTime")
        data = dt.datetime.fromisoformat(market_time).date() if market_time else dt.date.today()
        records.append(PriceRecord(ticker=f"{symbol}.SA", data=data, preco=float(price), fonte=FONTE))

    return records
