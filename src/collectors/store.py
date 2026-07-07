import datetime as dt

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from src.models import Instrument, Price


def get_or_create_instrument(
    session: Session,
    ticker: str,
    tipo: str,
    nome: str | None = None,
    fonte_primaria: str | None = None,
) -> Instrument:
    instrument = session.query(Instrument).filter_by(ticker=ticker).one_or_none()
    if instrument is not None:
        return instrument
    instrument = Instrument(ticker=ticker, tipo=tipo, nome=nome, fonte_primaria=fonte_primaria)
    session.add(instrument)
    session.flush()
    return instrument


def upsert_price(session: Session, instrument: Instrument, data: dt.date, preco: float, fonte: str) -> None:
    """Insere ou atualiza (instrument_id, data, fonte) — reprocessar o mesmo dia não duplica linhas."""
    stmt = insert(Price).values(
        instrument_id=instrument.id,
        data=data,
        preco=preco,
        fonte=fonte,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["instrument_id", "data", "fonte"],
        set_={"preco": preco},
    )
    session.execute(stmt)
