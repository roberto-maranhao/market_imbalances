from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Instrument, Pair
from src.signals.seed_pairs import ensure_pairs


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ensure_pairs_skips_when_instrument_missing():
    session = make_session()

    pairs = ensure_pairs(session, seeds=[("TIO=F", "VALE3.SA", "tese")])

    assert pairs == []
    assert session.query(Pair).count() == 0


def test_ensure_pairs_creates_and_is_idempotent():
    session = make_session()
    a = Instrument(ticker="TIO=F", tipo="commodity")
    b = Instrument(ticker="VALE3.SA", tipo="acao")
    session.add_all([a, b])
    session.commit()

    seeds = [("TIO=F", "VALE3.SA", "tese")]
    first = ensure_pairs(session, seeds=seeds)
    session.commit()
    second = ensure_pairs(session, seeds=seeds)
    session.commit()

    assert len(first) == 1
    assert first[0].id == second[0].id
    assert session.query(Pair).count() == 1
