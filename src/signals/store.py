from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from src.models import Pair, Signal
from src.signals.engine import PairSignal


def upsert_signal(session: Session, pair: Pair, result: PairSignal) -> None:
    stmt = insert(Signal).values(
        pair_id=pair.id,
        data=result.data,
        spread=result.spread,
        hedge_ratio=result.hedge_ratio,
        zscore=result.zscore,
        correlacao_movel=result.correlacao_movel,
        coint_pvalue=result.coint_pvalue,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["pair_id", "data"],
        set_={
            "spread": result.spread,
            "hedge_ratio": result.hedge_ratio,
            "zscore": result.zscore,
            "correlacao_movel": result.correlacao_movel,
            "coint_pvalue": result.coint_pvalue,
        },
    )
    session.execute(stmt)
