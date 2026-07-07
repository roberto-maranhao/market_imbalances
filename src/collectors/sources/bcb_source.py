import datetime as dt
import logging

from src.collectors.http import get_with_retry
from src.collectors.types import PriceRecord

logger = logging.getLogger(__name__)

FONTE = "bcb-sgs"
URL_TEMPLATE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/{n}?formato=json"

# séries SGS relevantes (ver plan.json -> data_sources.cambio / cestas_de_moedas)
SERIES = {
    "USDBRL_PTAX": 1,
    "EURBRL_PTAX": 21619,
    "IC_BR": 27574,
    "ITCR_BR": 11752,
}


def fetch_series(ticker: str, codigo: int, n: int = 5) -> list[PriceRecord]:
    url = URL_TEMPLATE.format(codigo=codigo, n=n)
    try:
        resp = get_with_retry(url)
    except Exception:
        logger.exception("BCB SGS: falha ao buscar série %s (%s)", codigo, ticker)
        return []

    records: list[PriceRecord] = []
    for item in resp.json():
        try:
            data = dt.datetime.strptime(item["data"], "%d/%m/%Y").date()
            preco = float(item["valor"])
        except (KeyError, ValueError):
            continue
        records.append(PriceRecord(ticker=ticker, data=data, preco=preco, fonte=FONTE))
    return records


def fetch_latest(series: dict[str, int] = SERIES) -> list[PriceRecord]:
    records: list[PriceRecord] = []
    for ticker, codigo in series.items():
        records.extend(fetch_series(ticker, codigo))
    return records
