from flask import Flask, abort, render_template

from src.config import FLASK_SECRET_KEY
from src.db import get_session
from src.models import Instrument, Pair
from src.signals.engine import align_series, compute_pair_series
from src.signals.loader import load_price_series
from src.web.charts import rebased_multi_series_chart, rolling_correlation_chart, scatter_chart, spread_zscore_chart

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

            return render_template(
                "pair_detail.html",
                pair=pair,
                has_data=True,
                n_obs=len(series),
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

    return app
