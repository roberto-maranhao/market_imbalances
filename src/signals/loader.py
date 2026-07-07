import pandas as pd
from sqlalchemy.orm import Session

from src.models import Instrument, Price


def load_price_series(session: Session, instrument: Instrument) -> pd.Series:
    rows = (
        session.query(Price.data, Price.preco)
        .filter_by(instrument_id=instrument.id)
        .order_by(Price.data)
        .all()
    )
    if not rows:
        return pd.Series(dtype=float)
    index = pd.DatetimeIndex([r.data for r in rows])
    return pd.Series([r.preco for r in rows], index=index, name=instrument.ticker)
