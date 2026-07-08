"""Monta figuras Plotly prontas para embutir no HTML a partir de séries pandas.

Cada função devolve uma string JSON (via Figure.to_json()) — o Jinja embute isso direto no
<script> com o filtro `safe` (não `tojson`: já é JSON válido, e tojson não sabe serializar os
tipos internos do Plotly). O JS do lado do cliente (ver base.html, função `renderPlot`) cuida
de tema claro/escuro e realmente desenha o gráfico via Plotly.newPlot.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.signals.engine import OpportunityEpisode

TREND_LINE_STYLE = {"dash": "dot", "width": 1.5}


def _fig_json(fig: go.Figure) -> str:
    fig.update_layout(margin=dict(l=55, r=55, t=10, b=10), hovermode="x unified", showlegend=True)
    return fig.to_json()


def _ols_trend(series: pd.Series) -> pd.Series:
    """Ajuste linear simples (mínimos quadrados) do valor contra o tempo — usado como linha de
    tendência opcional (escondida por padrão, ver visible='legendonly' nas chamadas)."""
    clean = series.dropna()
    if len(clean) < 2:
        return pd.Series(dtype=float)
    t = (clean.index - clean.index[0]).days.to_numpy(dtype=float)
    slope, intercept = np.polyfit(t, clean.to_numpy(dtype=float), 1)
    fitted = slope * t + intercept
    return pd.Series(fitted, index=clean.index)


def _episode_shapes(episodes: list[OpportunityEpisode], last_date) -> list[dict]:
    """Faixas verticais (shapes, não traces — não aparecem na legenda) marcando os episódios
    de oportunidade: laranja = z-score positivo, azul = z-score negativo."""
    shapes = []
    for ep in episodes:
        fim = ep.fim if ep.fim is not None else last_date
        cor = "rgba(230, 126, 34, 0.16)" if ep.pico_zscore > 0 else "rgba(52, 152, 219, 0.16)"
        shapes.append({
            "type": "rect", "xref": "x", "yref": "paper",
            "x0": ep.inicio.isoformat(), "x1": fim.isoformat() if hasattr(fim, "isoformat") else str(fim),
            "y0": 0, "y1": 1, "fillcolor": cor, "line": {"width": 0}, "layer": "below",
        })
    return shapes


def original_values_figure(
    series: pd.DataFrame,
    label_a: str,
    label_b: str,
    hedge_ratio: float,
    intercept: float,
    episodes: list[OpportunityEpisode],
) -> tuple[str, bool]:
    """Série 'raiz': os dois preços originais (sem z-score/rebase), cada um no seu próprio
    eixo y — a base concreta da qual o spread/z-score é derivado. O eixo B é calibrado a
    partir da própria regressão (a ~ hedge_ratio*b + intercept) quando isso não distorce
    demais a escala natural de B; senão cada eixo usa seu range natural (ver _axis_b_range)."""
    a, b = series["a"], series["b"]

    a_min, a_max = float(a.min()), float(a.max())
    a_pad = (a_max - a_min) * 0.05 or abs(a_max) * 0.05 or 1.0
    axis_a_range = [a_min - a_pad, a_max + a_pad]

    b_min, b_max = float(b.min()), float(b.max())
    b_pad = (b_max - b_min) * 0.05 or abs(b_max) * 0.05 or 1.0
    axis_b_natural = [b_min - b_pad, b_max + b_pad]

    axis_b_range = axis_b_natural
    calibrado = False
    if hedge_ratio:
        b_at_a_min = (axis_a_range[0] - intercept) / hedge_ratio
        b_at_a_max = (axis_a_range[1] - intercept) / hedge_ratio
        calibrated_width = abs(b_at_a_max - b_at_a_min)
        natural_width = axis_b_natural[1] - axis_b_natural[0]
        if natural_width and 0.4 <= calibrated_width / natural_width <= 4:
            axis_b_range = sorted([b_at_a_min, b_at_a_max])
            if hedge_ratio < 0:
                axis_b_range = axis_b_range[::-1]
            calibrado = True

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=a.index, y=a, name=label_a, yaxis="y", mode="lines",
        hovertemplate="%{y:.4g}<extra>" + label_a + "</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=b.index, y=b, name=label_b, yaxis="y2", mode="lines",
        hovertemplate="%{y:.4g}<extra>" + label_b + "</extra>",
    ))

    for label, raw in ((label_a, a), (label_b, b)):
        trend = _ols_trend(raw)
        if trend.empty:
            continue
        fig.add_trace(go.Scatter(
            x=trend.index, y=trend, name=f"Tendência — {label}", mode="lines",
            yaxis="y" if label == label_a else "y2",
            line=TREND_LINE_STYLE, visible="legendonly",
            hovertemplate="%{y:.4g}<extra>Tendência — " + label + "</extra>",
        ))

    last_date = series.index[-1].date()
    fig.update_layout(
        xaxis=dict(type="date"),
        yaxis=dict(title=label_a, range=axis_a_range),
        yaxis2=dict(title=label_b, overlaying="y", side="right", range=axis_b_range, showgrid=False),
        shapes=_episode_shapes(episodes, last_date),
        legend=dict(orientation="h", y=1.12, x=0),
    )
    return _fig_json(fig), calibrado


def spread_zscore_figure(series: pd.DataFrame, episodes: list[OpportunityEpisode]) -> str:
    """Gráfico de z-score do spread com bandas de referência em ±1/±2 desvios-padrão e uma
    média móvel opcional (escondida por padrão) como linha de tendência."""
    zscore = series["zscore"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=zscore.index, y=zscore, name="z-score do spread", mode="lines",
        line=dict(width=2), hovertemplate="%{y:.2f}<extra>z-score</extra>",
    ))

    trend = zscore.rolling(20, min_periods=5).mean()
    fig.add_trace(go.Scatter(
        x=trend.index, y=trend, name="Média móvel (20)", mode="lines",
        line=TREND_LINE_STYLE, visible="legendonly",
        hovertemplate="%{y:.2f}<extra>Média móvel (20)</extra>",
    ))

    last_date = series.index[-1].date()
    shapes = _episode_shapes(episodes, last_date)
    for level in (2, 1, -1, -2):
        shapes.append({
            "type": "line", "xref": "paper", "yref": "y",
            "x0": 0, "x1": 1, "y0": level, "y1": level,
            "line": {"color": "rgba(136, 136, 136, 0.6)", "width": 1, "dash": "dash"},
        })

    fig.update_layout(
        xaxis=dict(type="date"),
        yaxis=dict(title="z-score"),
        shapes=shapes,
    )
    return _fig_json(fig)


def scatter_figure(series: pd.DataFrame, label_a: str, label_b: str, hedge_ratio: float, intercept: float) -> str:
    """Dispersão A vs B com a própria reta ajustada (OLS) sobreposta — escondida por padrão,
    já que é a mesma regressão usada para calcular hedge_ratio/spread/z-score."""
    a, b = series["a"], series["b"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=b, y=a, mode="markers", name=f"{label_a} vs {label_b}",
        marker=dict(size=5, opacity=0.55),
        hovertemplate=f"{label_b}" + ": %{x:.4g}<br>" + f"{label_a}" + ": %{y:.4g}<extra></extra>",
    ))

    b_sorted = np.linspace(float(b.min()), float(b.max()), 50)
    fitted = hedge_ratio * b_sorted + intercept
    fig.add_trace(go.Scatter(
        x=b_sorted, y=fitted, name="Reta ajustada (OLS)", mode="lines",
        line=TREND_LINE_STYLE, visible="legendonly",
        hovertemplate="%{y:.4g}<extra>Reta ajustada</extra>",
    ))

    fig.update_layout(xaxis=dict(title=label_b), yaxis=dict(title=label_a))
    return _fig_json(fig)


def rolling_correlation_figure(series: pd.DataFrame) -> str:
    corr = series["correlacao_movel"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=corr.index, y=corr, name="Correlação móvel", mode="lines",
        hovertemplate="%{y:.2f}<extra>Correlação móvel</extra>",
    ))
    trend = corr.rolling(90, min_periods=10).mean()
    fig.add_trace(go.Scatter(
        x=trend.index, y=trend, name="Média móvel (90)", mode="lines",
        line=TREND_LINE_STYLE, visible="legendonly",
        hovertemplate="%{y:.2f}<extra>Média móvel (90)</extra>",
    ))
    fig.update_layout(
        xaxis=dict(type="date"),
        yaxis=dict(title="Correlação", range=[-1, 1]),
        shapes=[{
            "type": "line", "xref": "paper", "yref": "y",
            "x0": 0, "x1": 1, "y0": 0, "y1": 0,
            "line": {"color": "rgba(136, 136, 136, 0.4)", "width": 2},
        }],
    )
    return _fig_json(fig)


def rebased_multi_series_figure(series_by_label: dict[str, pd.Series]) -> str:
    """Cada série é rebasada a 100 no seu primeiro valor disponível, para comparar variação
    percentual (não nível absoluto) entre séries de escalas diferentes (câmbio, índices)."""
    fig = go.Figure()
    for label, series in series_by_label.items():
        series = series.sort_index()
        if series.empty:
            continue
        base = float(series.iloc[0])
        rebased = (series / base) * 100 if base else series
        fig.add_trace(go.Scatter(
            x=rebased.index, y=rebased, name=label, mode="lines",
            hovertemplate="%{y:.1f}<extra>" + label + "</extra>",
        ))
        trend = _ols_trend(rebased)
        if not trend.empty:
            fig.add_trace(go.Scatter(
                x=trend.index, y=trend, name=f"Tendência — {label}", mode="lines",
                line=TREND_LINE_STYLE, visible="legendonly",
                hovertemplate="%{y:.1f}<extra>Tendência — " + label + "</extra>",
            ))

    fig.update_layout(
        xaxis=dict(type="date"),
        yaxis=dict(title="Retorno acumulado (base 100)"),
    )
    return _fig_json(fig)


def thermometer_figure(raw_series: dict[str, pd.Series], basket_avg: pd.Series) -> str:
    """Cesta termômetro completa: cada ativo rebasado a 100 (linha fina) + a média da cesta
    em destaque (linha grossa) — eixo log, já que a dispersão de retornos entre os ativos
    (ex: NVDA vs. o resto) é grande demais pra uma escala linear mostrar todas as linhas."""
    fig = go.Figure()
    for label, series in raw_series.items():
        series = series.sort_index()
        base = float(series.iloc[0])
        rebased = (series / base) * 100 if base else series
        fig.add_trace(go.Scatter(
            x=rebased.index, y=rebased, name=label, mode="lines",
            line=dict(width=1.3), hovertemplate="%{y:.1f}<extra>" + label + "</extra>",
        ))

    fig.add_trace(go.Scatter(
        x=basket_avg.index, y=basket_avg, name="Cesta (média)", mode="lines",
        line=dict(width=3.5), hovertemplate="%{y:.1f}<extra>Cesta (média)</extra>",
    ))
    trend = _ols_trend(basket_avg)
    if not trend.empty:
        fig.add_trace(go.Scatter(
            x=trend.index, y=trend, name="Tendência — Cesta (média)", mode="lines",
            line=TREND_LINE_STYLE, visible="legendonly",
            hovertemplate="%{y:.1f}<extra>Tendência</extra>",
        ))

    fig.update_layout(
        xaxis=dict(type="date"),
        yaxis=dict(title="Retorno acumulado (base 100, escala log)", type="log"),
    )
    return _fig_json(fig)


def line_figure(series: pd.Series, label: str, y_tickformat: str | None = None) -> str:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, y=series, name=label, mode="lines",
        hovertemplate="%{y}<extra>" + label + "</extra>",
    ))
    trend = _ols_trend(series)
    if not trend.empty:
        fig.add_trace(go.Scatter(
            x=trend.index, y=trend, name=f"Tendência — {label}", mode="lines",
            line=TREND_LINE_STYLE, visible="legendonly",
            hovertemplate="%{y}<extra>Tendência</extra>",
        ))
    yaxis = dict(title=label)
    if y_tickformat:
        yaxis["tickformat"] = y_tickformat
    fig.update_layout(xaxis=dict(type="date"), yaxis=yaxis)
    return _fig_json(fig)
