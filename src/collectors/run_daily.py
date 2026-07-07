"""Job de coleta diária: busca preços/índices/fundamentals em todas as fontes
configuradas e grava em SQLite. Pensado para rodar via cron no Raspberry Pi.

Uso manual: python -m src.collectors.run_daily
"""

import logging

from src.collectors.sources import (
    bcb_source,
    brapi_source,
    edgar_source,
    fred_source,
    frankfurter_source,
    yfinance_source,
)
from src.collectors.store import get_or_create_instrument, upsert_price
from src.collectors.types import PriceRecord
from src.db import get_session, init_db

logger = logging.getLogger(__name__)

# --- universo de instrumentos coletados via yfinance (ver plan.json: theory.commodity_equity,
#     case_studies.spacex_ai_bubble) ---
YFINANCE_ACOES = [
    "VALE3.SA", "PETR4.SA",  # pares commodity-empresa (minério, petróleo)
    "BBDC3.SA", "BBDC4.SA",  # par ON/PN (mesma empresa, classes de ação diferentes)
    "SPCX", "RKLB", "ASTS", "GSAT", "VSAT", "STM",  # case study SpaceX
    "NVDA", "MSFT", "GOOGL", "AMZN", "META", "ORCL", "CRWV",  # bolha de IA: hyperscalers/chips
    "DLR", "EQIX", "IRM", "VST", "CEG", "GEV", "SMH",  # bolha de IA: termômetro (REITs, energia, ETF)
]
YFINANCE_COMMODITIES = ["TIO=F", "BZ=F", "CL=F", "GC=F", "ZS=F", "ZC=F"]
YFINANCE_FOREX = ["USDBRL=X", "EURBRL=X", "EURUSD=X"]
YFINANCE_INDICES = ["DX-Y.NYB"]

BRAPI_TICKERS = ["VALE3", "PETR4"]

TIPO_POR_TICKER: dict[str, str] = (
    {t: "acao" for t in YFINANCE_ACOES}
    | {t: "commodity" for t in YFINANCE_COMMODITIES}
    | {t: "forex" for t in YFINANCE_FOREX}
    | {t: "indice" for t in YFINANCE_INDICES}
    | {"USDBRL_PTAX": "forex", "EURBRL_PTAX": "forex", "IC_BR": "indice", "ITCR_BR": "indice"}
    | {
        "USDBRL_FRANKFURTER": "forex",
        "EURBRL_FRANKFURTER": "forex",
        "EURUSD_FRANKFURTER": "forex",
    }
    | {"DTWEXBGS": "indice"}
    | {
        f"{ticker}_{metric}": "fundamental"
        for ticker in edgar_source.CIKS
        for metric in edgar_source.METRICS
    }
)


def collect_all() -> dict[str, list[PriceRecord]]:
    """Chama cada fonte isoladamente — uma fonte falhando não derruba as outras."""
    resultados: dict[str, list[PriceRecord]] = {}

    fontes = {
        "yfinance": lambda: yfinance_source.fetch_latest(
            YFINANCE_ACOES + YFINANCE_COMMODITIES + YFINANCE_FOREX + YFINANCE_INDICES
        ),
        "brapi.dev": lambda: brapi_source.fetch_latest(BRAPI_TICKERS),
        "bcb-sgs": bcb_source.fetch_latest,
        "frankfurter": frankfurter_source.fetch_latest,
        "fred": fred_source.fetch_latest,
        "sec-edgar": edgar_source.fetch_latest,
    }

    for nome, fn in fontes.items():
        try:
            registros = fn()
        except Exception:
            logger.exception("Fonte %s falhou de forma inesperada (fora do retry interno)", nome)
            registros = []
        logger.info("Fonte %s: %d registros coletados", nome, len(registros))
        resultados[nome] = registros

    return resultados


def store_all(resultados: dict[str, list[PriceRecord]]) -> None:
    session = get_session()
    total = 0
    try:
        for nome_fonte, registros in resultados.items():
            for record in registros:
                tipo = TIPO_POR_TICKER.get(record.ticker, "indice")
                instrument = get_or_create_instrument(
                    session, ticker=record.ticker, tipo=tipo, fonte_primaria=record.fonte
                )
                upsert_price(session, instrument, record.data, record.preco, record.fonte)
                total += 1
        session.commit()
    finally:
        session.close()
    logger.info("Total de preços gravados/atualizados: %d", total)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    resultados = collect_all()
    store_all(resultados)


if __name__ == "__main__":
    main()
