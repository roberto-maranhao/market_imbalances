import logging

from src.collectors.types import PriceRecord
from src.config import FRED_API_KEY

logger = logging.getLogger(__name__)

FONTE = "fred"
SERIES = {
    "DTWEXBGS": "DTWEXBGS",  # Nominal Broad U.S. Dollar Index
}


def fetch_latest(series: dict[str, str] = SERIES) -> list[PriceRecord]:
    if not FRED_API_KEY:
        logger.info("FRED_API_KEY não configurada — pulando coleta FRED (ver .env.example)")
        return []

    from fredapi import Fred  # import tardio: evita custo se a fonte estiver desativada

    fred = Fred(api_key=FRED_API_KEY)
    records: list[PriceRecord] = []
    for ticker, series_id in series.items():
        try:
            data = fred.get_series_latest_release(series_id).dropna()
            if data.empty:
                continue
            last_date = data.index[-1].date()
            last_value = float(data.iloc[-1])
            records.append(PriceRecord(ticker=ticker, data=last_date, preco=last_value, fonte=FONTE))
        except Exception:
            logger.exception("FRED: falha ao buscar série %s", series_id)
    return records
