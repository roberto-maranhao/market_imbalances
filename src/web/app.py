import pandas as pd
from flask import Flask, abort, render_template, request

from src.config import FLASK_SECRET_KEY
from src.db import get_session
from src.models import Instrument, Pair
from src.signals.engine import (
    align_series,
    compute_coint_pvalue,
    compute_pair_series,
    detect_opportunity_episodes,
)
from src.signals.loader import load_price_series
from src.web.case_study import (
    capex_intensity_index,
    latest_snapshot_table,
    load_hyperscaler_series,
    thermometer_basket_index,
    thermometer_raw_series,
)
from src.web.charts import (
    line_figure,
    original_values_figure,
    rebased_multi_series_figure,
    rolling_correlation_figure,
    scatter_figure,
    spread_zscore_figure,
    thermometer_figure,
)
from src.web.interpretation import interpret_pair
from src.web.periods import PERIOD_OPTIONS, filter_period, period_link
from src.web.references import REFERENCES
from src.web.ticker_info import ticker_info

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
    app.jinja_env.globals["ticker_info"] = ticker_info
    app.jinja_env.globals["PERIOD_OPTIONS"] = PERIOD_OPTIONS
    app.jinja_env.globals["period_link"] = period_link

    @app.context_processor
    def inject_sidebar_pairs():
        # menu lateral lista os pares monitorados em toda página — uma query pequena (tabela
        # de ~5 linhas), roda em toda request, não vale a pena cada rota passar isso na mão.
        session = get_session()
        try:
            pairs = session.query(Pair).filter_by(ativo=True).order_by(Pair.id).all()
            sidebar_pairs = [
                {"id": p.id, "ticker_a": p.instrument_a.ticker, "ticker_b": p.instrument_b.ticker}
                for p in pairs
            ]
        finally:
            session.close()
        return {"sidebar_pairs": sidebar_pairs}

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

            # estatística ao vivo pro resumo teórico do painel — reaproveita os Signal já
            # carregados, sem query extra (ver objetivo 2: resumo da teoria no painel).
            com_coint = [r for r in rows if r["signal"] and r["signal"].coint_pvalue is not None]
            coint_significativos = sum(1 for r in com_coint if r["signal"].coint_pvalue < 0.05)

            return render_template(
                "opportunity_board.html",
                rows=rows,
                total_pares=len(rows),
                coint_significativos=coint_significativos,
            )
        finally:
            session.close()

    @app.route("/metodologia")
    def metodologia():
        session = get_session()
        try:
            pairs = session.query(Pair).filter_by(ativo=True).order_by(Pair.id).all()
            hipoteses = []
            for pair in pairs:
                ticker_a, ticker_b = pair.instrument_a.ticker, pair.instrument_b.ticker
                series_a = load_price_series(session, pair.instrument_a)
                series_b = load_price_series(session, pair.instrument_b)
                if series_a.empty or series_b.empty:
                    continue
                aligned = align_series(series_a, series_b)
                if len(aligned) < 2:
                    continue

                series = compute_pair_series(aligned)
                last = series.iloc[-1]
                zscore = float(last["zscore"]) if pd.notna(last["zscore"]) else None
                coint_pvalue = compute_coint_pvalue(aligned)
                hedge_ratio = float(last["hedge_ratio"])

                hipoteses.append({
                    "pair": pair,
                    "hedge_ratio": hedge_ratio,
                    "zscore": zscore,
                    "coint_pvalue": coint_pvalue,
                    "interpretacao": interpret_pair(
                        ticker_a, ticker_b, hedge_ratio, zscore, series["correlacao_movel"], coint_pvalue
                    ),
                })

            return render_template("metodologia.html", hipoteses=hipoteses, references=REFERENCES)
        finally:
            session.close()

    @app.route("/pair/<int:pair_id>")
    def pair_detail(pair_id: int):
        session = get_session()
        try:
            pair = session.get(Pair, pair_id)
            if pair is None:
                abort(404)

            periodo = request.args.get("periodo", "max")

            series_a = load_price_series(session, pair.instrument_a)
            series_b = load_price_series(session, pair.instrument_b)
            if series_a.empty or series_b.empty:
                return render_template("pair_detail.html", pair=pair, has_data=False, periodo=periodo)

            aligned = filter_period(align_series(series_a, series_b), periodo)
            if len(aligned) < 2:
                return render_template("pair_detail.html", pair=pair, has_data=False, periodo=periodo)

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

            hedge_ratio = float(last["hedge_ratio"])
            intercept = float(last["intercept"])

            summary = {
                "data_atual": series.index[-1].date(),
                "a_atual": float(last["a"]),
                "b_atual": float(last["b"]),
                "spread_medio": spread_medio,
                "spread_atual": float(last["spread"]),
                "desvio_padrao": std_spread,
                "zscore_atual": zscore_atual,
                "oportunidade_pct": oportunidade_pct,
                "hedge_ratio": hedge_ratio,
                "intercept": intercept,
            }

            episodes = detect_opportunity_episodes(series)
            original_fig, original_calibrado = original_values_figure(
                series, pair.instrument_a.ticker, pair.instrument_b.ticker, hedge_ratio, intercept, episodes
            )
            coint_pvalue = compute_coint_pvalue(aligned)
            interpretacao = interpret_pair(
                pair.instrument_a.ticker, pair.instrument_b.ticker,
                hedge_ratio, zscore_atual, series["correlacao_movel"], coint_pvalue,
            )

            return render_template(
                "pair_detail.html",
                pair=pair,
                has_data=True,
                n_obs=len(series),
                summary=summary,
                episodes=episodes,
                periodo=periodo,
                coint_pvalue=coint_pvalue,
                interpretacao=interpretacao,
                original_fig=original_fig,
                original_calibrado=original_calibrado,
                spread_fig=spread_zscore_figure(series, episodes),
                scatter_fig=scatter_figure(series, pair.instrument_a.ticker, pair.instrument_b.ticker, hedge_ratio, intercept),
                correlation_fig=rolling_correlation_figure(series),
            )
        finally:
            session.close()

    @app.route("/cambio")
    def currency_decomposition():
        session = get_session()
        try:
            periodo = request.args.get("periodo", "max")
            series_by_label = {}
            for label, ticker in CURRENCY_DECOMPOSITION_TICKERS.items():
                instrument = session.query(Instrument).filter_by(ticker=ticker).one_or_none()
                if instrument is None:
                    continue
                series = filter_period(load_price_series(session, instrument), periodo)
                if not series.empty:
                    series_by_label[label] = series

            fig = rebased_multi_series_figure(series_by_label) if series_by_label else None
            return render_template("currency_decomposition.html", fig=fig, periodo=periodo)
        finally:
            session.close()

    @app.route("/case-study/ia-bubble")
    def ai_bubble_case_study():
        session = get_session()
        try:
            # "Última leitura por empresa" é sempre o dado mais recente disponível — não faz
            # sentido recortá-la por período, então usa hyperscaler_series sem filtro.
            hyperscaler_series = load_hyperscaler_series(session)
            snapshot = latest_snapshot_table(hyperscaler_series)

            capex_periodo = request.args.get("capex_periodo", "max")
            hyperscaler_series_periodo = {
                ticker: {metric: filter_period(serie, capex_periodo) for metric, serie in metrics.items()}
                for ticker, metrics in hyperscaler_series.items()
            }
            capex_index = capex_intensity_index(hyperscaler_series_periodo)
            capex_fig = line_figure(capex_index, "Capex agregado / Receita agregada", y_tickformat=".0%") if not capex_index.empty else None

            cesta_periodo = request.args.get("cesta_periodo", "max")
            thermometer_series = {
                ticker: filter_period(serie, cesta_periodo)
                for ticker, serie in thermometer_raw_series(session).items()
            }
            basket_index = thermometer_basket_index(thermometer_series)
            basket_fig = thermometer_figure(thermometer_series, basket_index) if not basket_index.empty else None

            return render_template(
                "ai_bubble_case_study.html",
                snapshot=snapshot,
                capex_fig=capex_fig,
                capex_periodo=capex_periodo,
                basket_fig=basket_fig,
                cesta_periodo=cesta_periodo,
            )
        finally:
            session.close()

    return app
