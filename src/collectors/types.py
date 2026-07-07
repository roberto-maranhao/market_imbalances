import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class PriceRecord:
    ticker: str
    data: dt.date
    preco: float
    fonte: str
