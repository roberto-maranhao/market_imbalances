"""Recalcula o sinal (cointegração, hedge ratio, z-score, correlação móvel) de cada par
ativo a partir do histórico de preços em SQLite. Roda depois da coleta diária.

Uso manual: python -m src.signals.run_daily
"""

import logging

from src.db import get_session, init_db
from src.models import Pair
from src.signals.engine import align_series, compute_pair_signal
from src.signals.loader import load_price_series
from src.signals.seed_pairs import ensure_pairs
from src.signals.store import upsert_signal

logger = logging.getLogger(__name__)


def run() -> None:
    session = get_session()
    try:
        pairs = ensure_pairs(session)
        session.commit()

        for pair in pairs:
            pair = session.get(Pair, pair.id)  # recarrega com relationships após o commit
            series_a = load_price_series(session, pair.instrument_a)
            series_b = load_price_series(session, pair.instrument_b)

            if series_a.empty or series_b.empty:
                logger.warning(
                    "Par %s/%s sem preços suficientes — pulando",
                    pair.instrument_a.ticker, pair.instrument_b.ticker,
                )
                continue

            aligned = align_series(series_a, series_b)
            result = compute_pair_signal(aligned)
            if result is None:
                logger.warning(
                    "Par %s/%s tem só %d observações alinhadas (mínimo exigido: 20) — pulando",
                    pair.instrument_a.ticker, pair.instrument_b.ticker, len(aligned),
                )
                continue

            upsert_signal(session, pair, result)
            logger.info(
                "Par %s/%s: zscore=%.2f corr=%s coint_pvalue=%s (n=%d, data=%s)",
                pair.instrument_a.ticker, pair.instrument_b.ticker,
                result.zscore if result.zscore is not None else float("nan"),
                f"{result.correlacao_movel:.2f}" if result.correlacao_movel is not None else "n/a",
                f"{result.coint_pvalue:.4f}" if result.coint_pvalue is not None else "n/a",
                result.n_obs, result.data,
            )

        session.commit()
    finally:
        session.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    run()


if __name__ == "__main__":
    main()
