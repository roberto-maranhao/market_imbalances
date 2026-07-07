import datetime as dt
import logging

from src.collectors.http import get_with_retry
from src.collectors.types import PriceRecord

logger = logging.getLogger(__name__)

FONTE = "bcb-sgs"
URL_ULTIMOS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/{n}?formato=json"
URL_INTERVALO = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?dataInicial={inicio}&dataFinal={fim}&formato=json"

# séries SGS relevantes (ver plan.json -> data_sources.cambio / cestas_de_moedas)
SERIES = {
    "USDBRL_PTAX": 1,
    "EURBRL_PTAX": 21619,
    "IC_BR": 27574,
    "ITCR_BR": 11752,
}


def _parse_items(ticker: str, items: list[dict]) -> list[PriceRecord]:
    records: list[PriceRecord] = []
    for item in items:
        try:
            data = dt.datetime.strptime(item["data"], "%d/%m/%Y").date()
            preco = float(item["valor"])
        except (KeyError, ValueError):
            continue
        records.append(PriceRecord(ticker=ticker, data=data, preco=preco, fonte=FONTE))
    return records


def fetch_series(ticker: str, codigo: int, n: int = 5) -> list[PriceRecord]:
    """'Últimos N' — nota: o BCB limita esse endpoint a no máximo 20 pontos para algumas
    séries (ex: IC-Br, ITCR-BR). Bom para coleta incremental diária; para histórico maior,
    usar fetch_range."""
    url = URL_ULTIMOS.format(codigo=codigo, n=n)
    try:
        resp = get_with_retry(url)
    except Exception:
        logger.exception("BCB SGS: falha ao buscar série %s (%s)", codigo, ticker)
        return []
    return _parse_items(ticker, resp.json())


def fetch_range(ticker: str, codigo: int, data_inicial: dt.date, data_final: dt.date) -> list[PriceRecord]:
    """Endpoint por intervalo de datas — sem o teto de 20 pontos do 'ultimos/N'.
    Usado para backfill de histórico (ver src/collectors/backfill.py)."""
    url = URL_INTERVALO.format(
        codigo=codigo,
        inicio=data_inicial.strftime("%d/%m/%Y"),
        fim=data_final.strftime("%d/%m/%Y"),
    )
    try:
        resp = get_with_retry(url)
    except Exception:
        logger.exception("BCB SGS: falha ao buscar intervalo da série %s (%s)", codigo, ticker)
        return []
    return _parse_items(ticker, resp.json())


def fetch_latest(series: dict[str, int] = SERIES) -> list[PriceRecord]:
    records: list[PriceRecord] = []
    for ticker, codigo in series.items():
        records.extend(fetch_series(ticker, codigo))
    return records


def fetch_history(ticker: str, codigo: int, years: int = 5) -> list[PriceRecord]:
    """Histórico dos últimos `years` anos via endpoint de intervalo — usado para popular
    dados suficientes para o motor de sinais (ver src/signals)."""
    hoje = dt.date.today()
    inicio = hoje.replace(year=hoje.year - years)
    return fetch_range(ticker, codigo, inicio, hoje)
