import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.collectors.store import get_or_create_instrument, upsert_price
from src.models import Base, Price


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_get_or_create_instrument_is_idempotent():
    session = make_session()

    first = get_or_create_instrument(session, ticker="VALE3.SA", tipo="acao")
    session.commit()
    second = get_or_create_instrument(session, ticker="VALE3.SA", tipo="acao")
    session.commit()

    assert first.id == second.id
    assert session.query(Price).count() == 0


def test_upsert_price_updates_instead_of_duplicating():
    session = make_session()
    instrument = get_or_create_instrument(session, ticker="TIO=F", tipo="commodity")
    session.commit()

    day = dt.date(2026, 7, 1)
    upsert_price(session, instrument, day, 105.0, fonte="yfinance")
    session.commit()
    upsert_price(session, instrument, day, 106.5, fonte="yfinance")
    session.commit()

    prices = session.query(Price).filter_by(instrument_id=instrument.id, data=day).all()
    assert len(prices) == 1
    assert prices[0].preco == 106.5
