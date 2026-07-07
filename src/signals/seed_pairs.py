"""Pares monitorados pelo motor de sinais — ver plan.json:
theory.commodity_equity.examples, theory.currency, e roadmap fase 2."""

import logging

from sqlalchemy.orm import Session

from src.models import Instrument, Pair

logger = logging.getLogger(__name__)

# (ticker_a, ticker_b, tese_teorica)
PAIR_SEEDS: list[tuple[str, str, str]] = [
    (
        "TIO=F",
        "VALE3.SA",
        "Minério de ferro responde por ~70-80% da receita da Vale; correlação positiva "
        "esperada (beta>1 por alavancagem operacional), modulada por câmbio USD/BRL e "
        "risco-país específico.",
    ),
    (
        "BZ=F",
        "PETR4.SA",
        "Petróleo Brent vs Petrobras — correlação positiva, mas historicamente MENOS que "
        "proporcional por intervenção do governo na política de preços de combustíveis.",
    ),
    (
        "IC_BR",
        "USDBRL_PTAX",
        "BRL como moeda-commodity: deveria se apreciar (USDBRL cair) quando o índice de "
        "commodities exportadas pelo Brasil (IC-Br) sobe — efeito termos de troca.",
    ),
    (
        "DX-Y.NYB",
        "ITCR_BR",
        "Decomposição cambial: força global do USD (DXY) vs câmbio efetivo real do BRL "
        "(ITCR-BR/IREER) — isola o quanto do movimento do Real é idiossincrático.",
    ),
]


def ensure_pairs(session: Session, seeds: list[tuple[str, str, str]] = PAIR_SEEDS) -> list[Pair]:
    """Idempotente: cria os pares que ainda não existem. Os instrumentos referenciados
    precisam já existir (rodar src.collectors.backfill / run_daily antes)."""
    pairs: list[Pair] = []
    for ticker_a, ticker_b, tese in seeds:
        instrument_a = session.query(Instrument).filter_by(ticker=ticker_a).one_or_none()
        instrument_b = session.query(Instrument).filter_by(ticker=ticker_b).one_or_none()
        if instrument_a is None or instrument_b is None:
            logger.warning(
                "Par %s/%s pulado: instrumento(s) ainda não coletado(s) (rode backfill/run_daily primeiro)",
                ticker_a, ticker_b,
            )
            continue

        pair = (
            session.query(Pair)
            .filter_by(instrument_a_id=instrument_a.id, instrument_b_id=instrument_b.id)
            .one_or_none()
        )
        if pair is None:
            pair = Pair(instrument_a_id=instrument_a.id, instrument_b_id=instrument_b.id, tese_teorica=tese)
            session.add(pair)
            session.flush()
        pairs.append(pair)

    return pairs
