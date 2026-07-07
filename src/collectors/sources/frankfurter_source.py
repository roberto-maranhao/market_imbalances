import datetime as dt
import logging

from src.collectors.http import get_with_retry
from src.collectors.types import PriceRecord

logger = logging.getLogger(__name__)

FONTE = "frankfurter"
URL = "https://api.frankfurter.dev/v1/latest"

# (ticker de saída, moeda base, moeda alvo)
PAIRS = [
    ("USDBRL_FRANKFURTER", "USD", "BRL"),
    ("EURBRL_FRANKFURTER", "EUR", "BRL"),
    ("EURUSD_FRANKFURTER", "EUR", "USD"),
]


def fetch_pair(ticker: str, base: str, symbol: str) -> PriceRecord | None:
    try:
        resp = get_with_retry(URL, params={"base": base, "symbols": symbol})
    except Exception:
        logger.exception("Frankfurter: falha ao buscar %s/%s", base, symbol)
        return None

    payload = resp.json()
    rate = payload.get("rates", {}).get(symbol)
    if rate is None:
        logger.warning("Frankfurter: sem taxa %s/%s na resposta", base, symbol)
        return None

    data = dt.date.fromisoformat(payload["date"])
    return PriceRecord(ticker=ticker, data=data, preco=float(rate), fonte=FONTE)


def fetch_latest(pairs: list[tuple[str, str, str]] = PAIRS) -> list[PriceRecord]:
    records: list[PriceRecord] = []
    for ticker, base, symbol in pairs:
        record = fetch_pair(ticker, base, symbol)
        if record is not None:
            records.append(record)
    return records
