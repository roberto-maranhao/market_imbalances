import datetime as dt
import logging

import requests

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


def _get_json(url: str, ticker: str, codigo: int) -> list[dict] | None:
    """GET + parse JSON num único try/except — o BCB às vezes responde 200 com corpo vazio
    ou não-JSON (observado num backfill real), o que faria .json() estourar fora do
    try/except de get_with_retry se não fosse tratado aqui também."""
    try:
        resp = get_with_retry(url)
        return resp.json()
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            # o BCB usa 404 (em vez de uma lista vazia) quando a janela consultada
            # genuinamente não tem nenhum dado — comum no último "pedaço" pequeno de uma
            # série mensal ao paginar em blocos de anos. Não é falha, não vale ERROR/traceback.
            logger.info("BCB SGS: sem dados no intervalo para série %s (%s)", codigo, ticker)
            return []
        logger.exception("BCB SGS: falha ao buscar/parsear série %s (%s)", codigo, ticker)
        return None
    except Exception:
        logger.exception("BCB SGS: falha ao buscar/parsear série %s (%s)", codigo, ticker)
        return None


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
    items = _get_json(url, ticker, codigo)
    return _parse_items(ticker, items) if items is not None else []


def fetch_range(ticker: str, codigo: int, data_inicial: dt.date, data_final: dt.date) -> list[PriceRecord]:
    """Endpoint por intervalo de datas — sem o teto de 20 pontos do 'ultimos/N'.
    Usado para backfill de histórico (ver src/collectors/backfill.py)."""
    url = URL_INTERVALO.format(
        codigo=codigo,
        inicio=data_inicial.strftime("%d/%m/%Y"),
        fim=data_final.strftime("%d/%m/%Y"),
    )
    items = _get_json(url, ticker, codigo)
    return _parse_items(ticker, items) if items is not None else []


def fetch_latest(series: dict[str, int] = SERIES) -> list[PriceRecord]:
    records: list[PriceRecord] = []
    for ticker, codigo in series.items():
        records.extend(fetch_series(ticker, codigo))
    return records


MAX_JANELA_DIARIA_ANOS = 10  # limite do BCB para séries de periodicidade diária (ex: PTAX)


def fetch_history(ticker: str, codigo: int, years: int = 5) -> list[PriceRecord]:
    """Histórico dos últimos `years` anos via endpoint de intervalo — usado para popular
    dados suficientes para o motor de sinais (ver src/signals).

    Séries diárias (ex: PTAX) têm um teto de 10 anos por consulta no BCB; para janelas
    maiores, pagina em blocos de até 10 anos e concatena. Séries mensais (IC-Br, ITCR-BR)
    não têm esse teto, mas paginar não causa problema."""
    hoje = dt.date.today()
    inicio_total = hoje - dt.timedelta(days=int(365.25 * years))

    records: list[PriceRecord] = []
    chunk_inicio = inicio_total
    while chunk_inicio < hoje:
        chunk_fim = min(hoje, chunk_inicio + dt.timedelta(days=365 * MAX_JANELA_DIARIA_ANOS))
        records.extend(fetch_range(ticker, codigo, chunk_inicio, chunk_fim))
        chunk_inicio = chunk_fim + dt.timedelta(days=1)
    return records
