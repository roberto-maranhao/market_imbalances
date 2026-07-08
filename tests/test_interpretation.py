import pandas as pd

from src.web.interpretation import classify_hedge_ratio, correlation_trend, interpret_pair


def test_classify_hedge_ratio_consistente_for_operating_leverage_pair():
    label, _ = classify_hedge_ratio("TIO=F", "VALE3.SA", 1.5)
    assert label == "consistente"


def test_classify_hedge_ratio_parcial_when_positive_but_outside_range():
    label, _ = classify_hedge_ratio("TIO=F", "VALE3.SA", 0.5)
    assert label == "parcial"


def test_classify_hedge_ratio_inconsistente_when_wrong_sign():
    label, _ = classify_hedge_ratio("TIO=F", "VALE3.SA", -0.2)
    assert label == "inconsistente"


def test_classify_hedge_ratio_subproportional_passthrough():
    label, _ = classify_hedge_ratio("BZ=F", "PETR4.SA", 0.7)
    assert label == "consistente"


def test_classify_hedge_ratio_control_pair_near_one():
    label, _ = classify_hedge_ratio("BBDC3.SA", "BBDC4.SA", 1.0)
    assert label == "consistente"


def test_classify_hedge_ratio_commodity_currency_expects_negative():
    label, _ = classify_hedge_ratio("IC_BR", "USDBRL_PTAX", 76.96)
    assert label == "inconsistente"


def test_classify_hedge_ratio_diagnostic_pair_never_fails():
    label, _ = classify_hedge_ratio("DX-Y.NYB", "ITCR_BR", -3.2)
    assert label == "diagnostico"


def test_classify_hedge_ratio_unknown_pair_is_diagnostic():
    label, _ = classify_hedge_ratio("XXX", "YYY", 1.0)
    assert label == "diagnostico"


def test_correlation_trend_rising():
    values = [0.2] * 60 + [0.5] * 40
    series = pd.Series(values, index=pd.date_range("2026-01-01", periods=100))
    assert correlation_trend(series) == "subindo"


def test_correlation_trend_falling():
    values = [0.8] * 60 + [0.3] * 40
    series = pd.Series(values, index=pd.date_range("2026-01-01", periods=100))
    assert correlation_trend(series) == "caindo"


def test_correlation_trend_stable():
    series = pd.Series([0.6] * 100, index=pd.date_range("2026-01-01", periods=100))
    assert correlation_trend(series) == "estável"


def test_interpret_pair_returns_all_expected_keys():
    corr_series = pd.Series([0.9] * 100, index=pd.date_range("2026-01-01", periods=100))
    result = interpret_pair("TIO=F", "VALE3.SA", 1.2, 2.5, corr_series, 0.02)

    assert result["veredito_label"] == "consistente"
    assert "z-score" in result["zscore_texto"].lower() or "2.50" in result["zscore_texto"]
    assert "0.020" in result["cointegracao_texto"]
    assert "Sinal forte" in result["sintese"]


def test_interpret_pair_handles_missing_zscore():
    corr_series = pd.Series(dtype=float)
    result = interpret_pair("TIO=F", "VALE3.SA", 1.2, None, corr_series, None)

    assert "indisponível" in result["zscore_texto"]
    assert "insuficientes" in result["sintese"]
