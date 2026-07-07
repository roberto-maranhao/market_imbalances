"""Popula histórico (não só o último valor) para os instrumentos usados pelos pares
monitorados do motor de sinais (src/signals) — cointegração/z-score/correlação móvel
precisam de dezenas de observações, e o job diário (run_daily.py) só traz os últimos dias.

Uso manual, roda uma vez (ou esporadicamente): python -m src.collectors.backfill
"""

import logging

from src.collectors.run_daily import TIPO_POR_TICKER
from src.collectors.sources import bcb_source, yfinance_source
from src.collectors.store import get_or_create_instrument, upsert_price
from src.collectors.types import PriceRecord
from src.db import get_session, init_db

logger = logging.getLogger(__name__)

YFINANCE_TICKERS = ["TIO=F", "VALE3.SA", "BZ=F", "PETR4.SA", "DX-Y.NYB"]

BCB_SERIES = {
    "USDBRL_PTAX": bcb_source.SERIES["USDBRL_PTAX"],
    "IC_BR": bcb_source.SERIES["IC_BR"],
    "ITCR_BR": bcb_source.SERIES["ITCR_BR"],
}


def collect(period: str = "2y", years: int = 5) -> list[PriceRecord]:
    records = yfinance_source.fetch_history(YFINANCE_TICKERS, period=period)
    for ticker, codigo in BCB_SERIES.items():
        records.extend(bcb_source.fetch_history(ticker, codigo, years=years))
    return records


def store(records: list[PriceRecord]) -> None:
    session = get_session()
    try:
        for record in records:
            tipo = TIPO_POR_TICKER.get(record.ticker, "indice")
            instrument = get_or_create_instrument(
                session, ticker=record.ticker, tipo=tipo, fonte_primaria=record.fonte
            )
            upsert_price(session, instrument, record.data, record.preco, record.fonte)
        session.commit()
    finally:
        session.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    records = collect()
    logger.info("Backfill: %d registros históricos coletados", len(records))
    store(records)
    logger.info("Backfill concluído")


if __name__ == "__main__":
    main()
