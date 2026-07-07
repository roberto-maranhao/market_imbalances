import datetime as dt
import logging
import re

from src.collectors.http import get_with_retry
from src.collectors.types import PriceRecord

logger = logging.getLogger(__name__)

FONTE = "sec-edgar"

# SEC exige um User-Agent descritivo com contato (https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
USER_AGENT = "market_imbalances research project rmaranhao@gmail.com"

URL_TEMPLATE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# CIKs (10 dígitos, zero-padded) dos hyperscalers monitorados no case study SpaceX/bolha de IA
CIKS = {
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
    "NVDA": "0001045810",
    "ORCL": "0001341439",
}

# tag XBRL -> sufixo de ticker sintético; múltiplas tags candidatas por métrica (nem toda empresa usa a mesma tag)
METRICS = {
    "CAPEX": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "REVENUE": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"],
}


def _duration_days(entry: dict) -> int:
    start, end = entry.get("start"), entry.get("end")
    if not start or not end:
        return 0
    return (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days


def _pick_canonical(entries: list[dict]) -> dict:
    """Entre entradas com o mesmo 'end', a SEC pode reportar tanto o período-padrão
    (trimestre/ano fiscal) quanto variantes como trailing-twelve-months, com o mesmo 'end'
    mas 'start' diferente. Entradas com 'frame' preenchido são as que a SEC marca como o
    período-calendário canônico; na ausência de uma, usa a de menor duração (evita pegar um
    TTM em vez do trimestre)."""
    framed = [e for e in entries if e.get("frame")]
    if framed:
        return framed[0]
    return min(entries, key=_duration_days)


def _latest_usd_value(facts: dict, tags: list[str]) -> tuple[str, float] | None:
    """Considera todas as tags candidatas (empresas trocam de tag XBRL ao longo do tempo,
    ex: 'Revenues' -> 'RevenueFromContractWithCustomerExcludingAssessedTax') e retorna a
    entrada com a data 'end' mais recente entre todas elas — nunca a de uma tag antiga."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    best: dict | None = None
    for tag in tags:
        units = us_gaap.get(tag, {}).get("units", {}).get("USD")
        if not units:
            continue
        max_end = max(item.get("end", "") for item in units)
        candidate = _pick_canonical([item for item in units if item.get("end", "") == max_end])
        if best is None or candidate.get("end", "") > best.get("end", ""):
            best = candidate
    if best is None:
        return None
    return best["end"], float(best["val"])


def _fetch_facts(ticker: str, cik: str) -> dict | None:
    url = URL_TEMPLATE.format(cik=cik)
    try:
        resp = get_with_retry(url, headers={"User-Agent": USER_AGENT})
    except Exception:
        logger.exception("SEC EDGAR: falha ao buscar companyfacts de %s (CIK %s)", ticker, cik)
        return None
    return resp.json()


_QUARTER_FRAME_RE = re.compile(r"^CY\d{4}Q[1-4]$")


def _all_framed_values(facts: dict, tags: list[str]) -> list[tuple[str, float]]:
    """Todas as entradas TRIMESTRAIS com 'frame' (período-calendário canônico da SEC) entre
    as tags candidatas — não só a mais recente. Usado para reconstruir uma série histórica
    trimestral (ver fetch_history / case study da bolha de IA).

    Só aceita frames no formato 'CYyyyyQn': a SEC também marca o total ANUAL (10-K) com
    frame 'CYyyyy' (sem 'Qn') no mesmo 'end' de dezembro do Q4 — sem filtrar por esse
    padrão, o valor anual (~4x maior) entraria na série como se fosse o trimestre."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    by_end: dict[str, float] = {}
    for tag in tags:
        units = us_gaap.get(tag, {}).get("units", {}).get("USD", [])
        for item in units:
            end = item.get("end")
            frame = item.get("frame")
            if end and frame and _QUARTER_FRAME_RE.match(frame) and end not in by_end:
                by_end[end] = float(item["val"])
    return sorted(by_end.items())


def fetch_latest(
    companies: dict[str, str] = CIKS,
    metrics: dict[str, list[str]] = METRICS,
) -> list[PriceRecord]:
    records: list[PriceRecord] = []

    for ticker, cik in companies.items():
        facts = _fetch_facts(ticker, cik)
        if facts is None:
            continue

        for metric_name, tags in metrics.items():
            result = _latest_usd_value(facts, tags)
            if result is None:
                logger.warning("SEC EDGAR: nenhuma tag %s encontrada para %s", tags, ticker)
                continue
            end_date, value = result
            records.append(
                PriceRecord(
                    ticker=f"{ticker}_{metric_name}",
                    data=dt.date.fromisoformat(end_date),
                    preco=value,
                    fonte=FONTE,
                )
            )

    return records


def fetch_history(
    companies: dict[str, str] = CIKS,
    metrics: dict[str, list[str]] = METRICS,
) -> list[PriceRecord]:
    """Toda a série trimestral disponível (não só o valor mais recente) — usada para
    montar o índice de intensidade de capex de IA ao longo do tempo (case study). Nem toda
    empresa reporta a mesma tag por trimestre (ex: Oracle só reporta capex anualmente no
    10-K) — trimestres sem dado ficam ausentes para aquela empresa, não zerados."""
    records: list[PriceRecord] = []

    for ticker, cik in companies.items():
        facts = _fetch_facts(ticker, cik)
        if facts is None:
            continue

        for metric_name, tags in metrics.items():
            for end_date, value in _all_framed_values(facts, tags):
                records.append(
                    PriceRecord(
                        ticker=f"{ticker}_{metric_name}",
                        data=dt.date.fromisoformat(end_date),
                        preco=value,
                        fonte=FONTE,
                    )
                )

    return records
