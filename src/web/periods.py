"""Filtro de período compartilhado pelas páginas com gráficos de série temporal.

Trocar de aba não é um zoom visual sobre os números do histórico inteiro — isso seria
enganoso, já que z-score, hedge_ratio, correlação móvel e o próprio rebase (base 100) sempre
dependem da janela usada pra calculá-los. Por isso as rotas recortam a série ANTES de rodar o
motor de sinais/rebase para cada período, recalculando a análise inteira, não só o desenho."""

import datetime as dt
from urllib.parse import urlencode

PERIOD_OPTIONS = [
    ("1m", "1 mês", 30),
    ("6m", "6 meses", 182),
    ("1a", "1 ano", 365),
    ("5a", "5 anos", 1825),
    ("10a", "10 anos", 3650),
    ("max", "Máx", None),
]
_DAYS_BY_KEY = {key: days for key, _, days in PERIOD_OPTIONS}


def filter_period(data, periodo: str | None):
    """Recorta um pandas Series/DataFrame indexado por data aos últimos N dias a partir da
    última data disponível. periodo desconhecido, None ou 'max' devolve os dados inteiros."""
    days = _DAYS_BY_KEY.get(periodo)
    if not days or data.empty:
        return data
    cutoff = data.index[-1] - dt.timedelta(days=days)
    return data[data.index >= cutoff]


def period_link(current_args: dict, param_name: str, key: str) -> str:
    """Monta a query string do link de uma aba de período, preservando os outros parâmetros
    já presentes na URL (ex: numa página com dois seletores de período independentes)."""
    merged = {**current_args, param_name: key}
    return "?" + urlencode(merged)
