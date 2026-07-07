import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Instrument, Pair, Price, Signal


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_instrument_and_price_roundtrip():
    session = make_session()

    vale = Instrument(ticker="VALE3.SA", tipo="acao", nome="Vale", fonte_primaria="brapi.dev")
    session.add(vale)
    session.commit()

    session.add(Price(instrument_id=vale.id, data=dt.date(2026, 7, 1), preco=62.5, fonte="brapi.dev"))
    session.commit()

    fetched = session.query(Instrument).filter_by(ticker="VALE3.SA").one()
    assert len(fetched.prices) == 1
    assert fetched.prices[0].preco == 62.5


def test_pair_and_signal_roundtrip():
    session = make_session()

    iron_ore = Instrument(ticker="TIO=F", tipo="commodity", nome="Iron Ore 62% Fe")
    vale = Instrument(ticker="VALE3.SA", tipo="acao", nome="Vale")
    session.add_all([iron_ore, vale])
    session.commit()

    pair = Pair(
        instrument_a_id=iron_ore.id,
        instrument_b_id=vale.id,
        tese_teorica="Minério de ferro responde por ~70-80% da receita da Vale",
    )
    session.add(pair)
    session.commit()

    session.add(
        Signal(
            pair_id=pair.id,
            data=dt.date(2026, 7, 1),
            spread=1.23,
            hedge_ratio=0.85,
            zscore=2.1,
            correlacao_movel=0.76,
            coint_pvalue=0.02,
        )
    )
    session.commit()

    fetched = session.query(Pair).filter_by(id=pair.id).one()
    assert fetched.ativo is True
    assert len(fetched.signals) == 1
    assert fetched.signals[0].zscore == 2.1
