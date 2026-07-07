import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Instrument(Base):
    """Um ativo rastreado: ação, commodity, par de câmbio ou índice/cesta."""

    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(16))  # acao | commodity | forex | indice
    nome: Mapped[str | None] = mapped_column(String(128), default=None)
    fonte_primaria: Mapped[str | None] = mapped_column(String(64), default=None)

    prices: Mapped[list["Price"]] = relationship(back_populates="instrument")


class Price(Base):
    """Uma cotação de um instrumento numa data, vinda de uma fonte específica."""

    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint("instrument_id", "data", "fonte", name="uq_price_instrument_data_fonte"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True)
    data: Mapped[dt.date] = mapped_column(Date, index=True)
    preco: Mapped[float] = mapped_column(Float)
    fonte: Mapped[str] = mapped_column(String(64))
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    instrument: Mapped["Instrument"] = relationship(back_populates="prices")


class Pair(Base):
    """Um par teórico monitorado (ex: minério de ferro x Vale)."""

    __tablename__ = "pairs"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_a_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"))
    instrument_b_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"))
    tese_teorica: Mapped[str | None] = mapped_column(String(512), default=None)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    instrument_a: Mapped["Instrument"] = relationship(foreign_keys=[instrument_a_id])
    instrument_b: Mapped["Instrument"] = relationship(foreign_keys=[instrument_b_id])
    signals: Mapped[list["Signal"]] = relationship(back_populates="pair")


class Signal(Base):
    """Sinal calculado para um par numa data: spread, hedge ratio, z-score etc."""

    __tablename__ = "signals"
    __table_args__ = (UniqueConstraint("pair_id", "data", name="uq_signal_pair_data"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pair_id: Mapped[int] = mapped_column(ForeignKey("pairs.id"), index=True)
    data: Mapped[dt.date] = mapped_column(Date, index=True)
    spread: Mapped[float | None] = mapped_column(Float, default=None)
    hedge_ratio: Mapped[float | None] = mapped_column(Float, default=None)
    zscore: Mapped[float | None] = mapped_column(Float, default=None)
    correlacao_movel: Mapped[float | None] = mapped_column(Float, default=None)
    coint_pvalue: Mapped[float | None] = mapped_column(Float, default=None)

    pair: Mapped["Pair"] = relationship(back_populates="signals")
