import pandas as pd
from flask import Flask, abort, render_template

from src.config import FLASK_SECRET_KEY
from src.db import get_session
from src.models import Instrument, Pair
from src.signals.engine import align_series, compute_pair_series, detect_opportunity_episodes
from src.signals.loader import load_price_series
from src.web.case_study import (
    capex_intensity_index,
    latest_snapshot_table,
    load_hyperscaler_series,
    thermometer_basket_index,
)
from src.web.charts import (
    line_dataset,
    rebased_multi_series_chart,
    rolling_correlation_chart,
    scatter_chart,
    spread_zscore_chart,
)

# tickers usados na página de decomposição cambial (ver plan.json -> visualizations, "Decomposição cambial")
CURRENCY_DECOMPOSITION_TICKERS = {
    "USD/BRL (PTAX)": "USDBRL_PTAX",
    "DXY (cesta USD)": "DX-Y.NYB",
    "ITCR-BR / IREER (câmbio efetivo real)": "ITCR_BR",
    "IC-Br (commodities)": "IC_BR",
}


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = FLASK_SECRET_KEY

    @app.route("/")
    def opportunity_board():
        session = get_session()
        try:
            pairs = session.query(Pair).filter_by(ativo=True).all()
            rows = []
            for pair in pairs:
                latest = max(pair.signals, key=lambda s: s.data, default=None)
                rows.append({"pair": pair, "signal": latest})
            rows.sort(key=lambda r: abs(r["signal"].zscore) if r["signal"] and r["signal"].zscore is not None else -1, reverse=True)
            return render_template("opportunity_board.html", rows=rows)
        finally:
            session.close()

    @app.route("/pair/<int:pair_id>")
    def pair_detail(pair_id: int):
        session = get_session()
        try:
            pair = session.get(Pair, pair_id)
            if pair is None:
                abort(404)

            series_a = load_price_series(session, pair.instrument_a)
            series_b = load_price_series(session, pair.instrument_b)
            if series_a.empty or series_b.empty:
                return render_template("pair_detail.html", pair=pair, has_data=False)

            aligned = align_series(series_a, series_b)
            if len(aligned) < 2:
                return render_template("pair_detail.html", pair=pair, has_data=False)

            series = compute_pair_series(aligned)
            last = series.iloc[-1]
            std_spread = float(series["spread"].std(ddof=1))
            zscore_atual = float(last["zscore"]) if pd.notna(last["zscore"]) else None

            # se o spread voltasse à média histórica (mantendo B parado), de quanto A teria
            # que se mover — expresso em % do preço atual de A. É a estimativa de "tamanho
            # da oportunidade" pedida: distância atual até a média, em termos concretos.
            oportunidade_pct = None
            if zscore_atual is not None and last["a"]:
                oportunidade_pct = -(zscore_atual * std_spread) / float(last["a"]) * 100

            # o resíduo de uma regressão OLS tem média ~0 por construção — arredonda para
            # não mostrar ruído de ponto flutuante tipo "-2.9e-15" como se fosse um valor real
            spread_medio = float(series["spread"].mean())
            spread_medio = 0.0 if abs(spread_medio) < 1e-6 else spread_medio

            summary = {
                "data_atual": series.index[-1].date(),
                "a_atual": float(last["a"]),
                "b_atual": float(last["b"]),
                "spread_medio": spread_medio,
                "spread_atual": float(last["spread"]),
                "desvio_padrao": std_spread,
                "zscore_atual": zscore_atual,
                "oportunidade_pct": oportunidade_pct,
            }

            episodes = detect_opportunity_episodes(series)

            return render_template(
                "pair_detail.html",
                pair=pair,
                has_data=True,
                n_obs=len(series),
                summary=summary,
                episodes=episodes,
                spread_chart=spread_zscore_chart(series),
                scatter=scatter_chart(series, pair.instrument_a.ticker, pair.instrument_b.ticker),
                correlation_chart=rolling_correlation_chart(series),
            )
        finally:
            session.close()

    @app.route("/cambio")
    def currency_decomposition():
        session = get_session()
        try:
            series_by_label = {}
            for label, ticker in CURRENCY_DECOMPOSITION_TICKERS.items():
                instrument = session.query(Instrument).filter_by(ticker=ticker).one_or_none()
                if instrument is None:
                    continue
                series = load_price_series(session, instrument)
                if not series.empty:
                    series_by_label[label] = series

            chart = rebased_multi_series_chart(series_by_label) if series_by_label else None
            return render_template("currency_decomposition.html", chart=chart)
        finally:
            session.close()

    @app.route("/case-study/ia-bubble")
    def ai_bubble_case_study():
        session = get_session()
        try:
            hyperscaler_series = load_hyperscaler_series(session)
            snapshot = latest_snapshot_table(hyperscaler_series)

            capex_index = capex_intensity_index(hyperscaler_series)
            capex_chart = line_dataset(capex_index, "Capex agregado / Receita agregada") if not capex_index.empty else None

            basket_index = thermometer_basket_index(session)
            basket_chart = line_dataset(basket_index, "Cesta termômetro (retorno acumulado, base 100)") if not basket_index.empty else None

            return render_template(
                "ai_bubble_case_study.html",
                snapshot=snapshot,
                capex_chart=capex_chart,
                basket_chart=basket_chart,
            )
        finally:
            session.close()

    return app
