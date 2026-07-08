"""Leitura dinâmica dos 4 indicadores de cada par (z-score, correlação móvel, p-valor de
cointegração, hedge ratio), ancorada no referencial teórico do projeto (ver references.py e
/metodologia) e na hipótese específica de cada par. Nada aqui é texto fixo: os limiares e
citações são fixos, mas a leitura (força do sinal, consistência com a hipótese) é computada a
partir dos valores atuais — e do período selecionado (ver src/web/periods.py)."""

import pandas as pd

# (ticker_a, ticker_b) -> hipótese teórica sobre o hedge ratio esperado para esse par.
# faixa_esperada = (low, high) em que o hedge ratio "confirma" a hipótese; None = sem limite
# nessa ponta. diagnostico=True pula a classificação consistente/inconsistente (não é uma
# aposta direcional, ver DX-Y.NYB/ITCR_BR).
PAIR_HYPOTHESES: dict[tuple[str, str], dict] = {
    ("TIO=F", "VALE3.SA"): {
        "titulo": "H1 — Alavancagem operacional (minério de ferro → Vale)",
        "hipotese": (
            "Minério de ferro responde por ~70-80% da receita da Vale; a teoria de alavancagem "
            "operacional prevê que a ação amplifique o movimento da commodity."
        ),
        "faixa_esperada": (1.0, None),
        "direcao_texto": "hedge ratio > 1 (amplificação por alavancagem operacional)",
        "diagnostico": False,
    },
    ("BZ=F", "PETR4.SA"): {
        "titulo": "H2 — Repasse parcial por intervenção governamental (Brent → Petrobras)",
        "hipotese": (
            "Diferente de uma petrolífera privada, a política de preços de combustíveis do "
            "governo brasileiro historicamente amortece o repasse do Brent para a PETR4."
        ),
        "faixa_esperada": (0.0, 1.0),
        "direcao_texto": "0 < hedge ratio < 1 (repasse parcial por controle de preços)",
        "diagnostico": False,
    },
    ("BBDC3.SA", "BBDC4.SA"): {
        "titulo": "H3 — Par de controle (mesma empresa, duas classes de ação)",
        "hipotese": (
            "Por serem a mesma empresa, este é o par que a teoria prevê como cointegração mais "
            "'limpa' de todos monitorados: hedge ratio próximo de 1, menor p-valor de "
            "cointegração e correlação mais alta e estável entre os cinco pares."
        ),
        "faixa_esperada": (0.85, 1.15),
        "direcao_texto": "hedge ratio ≈ 1 (mesma empresa, mesmos fundamentos)",
        "diagnostico": False,
    },
    ("IC_BR", "USDBRL_PTAX"): {
        "titulo": "H4 — BRL como moeda-commodity (Chen & Rogoff, 2003)",
        "hipotese": (
            "Segundo a teoria de moeda-commodity, o Real deveria se apreciar (USDBRL cair) "
            "quando os preços de commodities exportadas pelo Brasil sobem (IC-Br em alta) — "
            "efeito termos de troca, o que implicaria hedge ratio negativo nesta regressão."
        ),
        "faixa_esperada": (None, 0.0),
        "direcao_texto": "hedge ratio < 0 (relação inversa, efeito termos de troca)",
        "diagnostico": False,
        "nota": (
            "Em janelas muito longas (ex: 'Máx', ~20 anos), o hedge ratio observado pode aparecer "
            "positivo mesmo que H4 esteja correta no curto prazo — isso tende a refletir "
            "tendências nominais próprias de cada série (inflação, depreciação estrutural do "
            "BRL), não necessariamente a quebra do mecanismo de termos de troca. Vale comparar "
            "com uma aba de período mais curta antes de descartar a hipótese."
        ),
    },
    ("DX-Y.NYB", "ITCR_BR"): {
        "titulo": "Par diagnóstico — decomposição cambial",
        "hipotese": (
            "Este par não é uma aposta direcional: mede quanto do movimento do câmbio efetivo "
            "real do Brasil (ITCR-BR/IREER) acompanha a força global do dólar (DXY), isolando o "
            "componente idiossincrático do Real."
        ),
        "faixa_esperada": None,
        "direcao_texto": None,
        "diagnostico": True,
    },
}


def classify_hedge_ratio(ticker_a: str, ticker_b: str, hedge_ratio: float) -> tuple[str, str]:
    """Compara o hedge ratio observado com a faixa esperada da hipótese do par. Devolve
    (rótulo, explicação); rótulo é um de consistente / parcial / inconsistente / diagnostico."""
    info = PAIR_HYPOTHESES.get((ticker_a, ticker_b))
    if info is None or info.get("diagnostico"):
        return "diagnostico", "Este par é uma leitura diagnóstica, não uma aposta direcional."

    low, high = info["faixa_esperada"]
    dentro_da_faixa = (low is None or hedge_ratio > low) and (high is None or hedge_ratio < high)
    if dentro_da_faixa:
        return "consistente", f"Hedge ratio de {hedge_ratio:.3f} está dentro do esperado ({info['direcao_texto']})."

    mesmo_sinal_geral = (low is not None and low >= 0 and hedge_ratio > 0) or (
        high is not None and high <= 0 and hedge_ratio < 0
    )
    if mesmo_sinal_geral:
        return (
            "parcial",
            f"Hedge ratio de {hedge_ratio:.3f} tem o sinal certo, mas fora da faixa exata "
            f"esperada ({info['direcao_texto']}) neste período.",
        )

    return (
        "inconsistente",
        f"Hedge ratio de {hedge_ratio:.3f} contraria a direção esperada "
        f"({info['direcao_texto']}) neste período.",
    )


def correlation_trend(corr_series: pd.Series, lookback: int = 60, limiar: float = 0.1) -> str:
    """Compara a correlação móvel atual com o valor de `lookback` observações atrás. Do & Faff
    (2010): correlação em queda estrutural é sinal de 'risco de sincronização', não só ruído."""
    clean = corr_series.dropna()
    if len(clean) < 2:
        return "indeterminada"
    atual = float(clean.iloc[-1])
    idx_anterior = max(0, len(clean) - 1 - lookback)
    anterior = float(clean.iloc[idx_anterior])
    delta = atual - anterior
    if delta > limiar:
        return "subindo"
    if delta < -limiar:
        return "caindo"
    return "estável"


def _forca_do_sinal(
    zscore: float | None, corr_atual: float | None, tendencia_corr: str, coint_pvalue: float | None
) -> str:
    if zscore is None:
        return "Dados insuficientes nesse período para avaliar a força do sinal."

    esticado = abs(zscore) >= 2.0
    if not esticado:
        return (
            "Sinal fraco: o z-score ainda não está esticado (|z| < 2) — pela régua deste "
            "projeto (Vidyamurthy, 2004), não há oportunidade aberta agora."
        )

    coint_ok = coint_pvalue is not None and coint_pvalue < 0.05
    corr_ok = tendencia_corr in ("subindo", "estável") and (corr_atual is None or corr_atual > 0.5)

    if coint_ok and corr_ok:
        return (
            "Sinal forte: z-score esticado, cointegração estatisticamente significativa "
            "(p<0.05) e correlação recente estável/alta — as três condições reforçam a leitura "
            "de reversão à média."
        )
    if coint_ok or corr_ok:
        return (
            "Sinal moderado: z-score esticado, mas só uma das outras duas condições "
            "(cointegração significativa ou correlação estável) dá suporte — trate com "
            "alguma cautela."
        )
    return (
        "Sinal fraco apesar do z-score esticado: sem cointegração significativa e/ou "
        "correlação em queda — pode ser quebra estrutural da relação, não oportunidade de "
        "reversão (Do & Faff, 2010)."
    )


def interpret_pair(
    ticker_a: str,
    ticker_b: str,
    hedge_ratio: float,
    zscore: float | None,
    corr_series: pd.Series,
    coint_pvalue: float | None,
) -> dict:
    """Monta a leitura dinâmica dos 4 indicadores para este par, ancorada no referencial
    teórico e na hipótese específica do par — usada tanto na página do par quanto no resumo
    ao vivo da /metodologia."""
    info = PAIR_HYPOTHESES.get((ticker_a, ticker_b), {})
    label, hedge_explicacao = classify_hedge_ratio(ticker_a, ticker_b, hedge_ratio)
    tendencia_corr = correlation_trend(corr_series)
    corr_limpa = corr_series.dropna()
    corr_atual = float(corr_limpa.iloc[-1]) if not corr_limpa.empty else None

    if zscore is None:
        zscore_texto = "z-score indisponível para esse período (histórico insuficiente)."
    else:
        esticado = abs(zscore) >= 2.0
        zscore_texto = (
            f"z-score atual de {zscore:+.2f}. Segundo Vidyamurthy (2004) e Gatev, Goetzmann & "
            f"Rouwenhorst (2006), |z| ≥ 2 marca abertura de oportunidade "
            f"({'está esticado agora' if esticado else 'ainda dentro da faixa normal'}); "
            f"|z| ≤ 0.5 marca o spread normalizado."
        )

    if corr_atual is None:
        corr_texto = "Correlação móvel indisponível para esse período."
    else:
        corr_texto = (
            f"Correlação móvel atual de {corr_atual:.2f}, {tendencia_corr} frente a ~60 "
            f"observações atrás. Do & Faff (2010) mostram que correlação em queda estrutural é "
            f"sinal de 'risco de sincronização' — a relação pode estar se rompendo, o que torna "
            f"qualquer z-score esticado menos confiável."
        )

    if coint_pvalue is None:
        coint_texto = "P-valor de cointegração indisponível para esse período (poucas observações)."
    else:
        significativo = coint_pvalue < 0.05
        coint_texto = f"P-valor de cointegração (Engle & Granger, 1987) de {coint_pvalue:.3f} — " + (
            "abaixo de 0.05, evidência estatística de que o spread reverte à média no longo prazo."
            if significativo
            else "acima de 0.05, sem evidência forte de reversão de longo prazo neste período; "
            "um z-score esticado aqui é menos confiável do que num par com p-valor baixo."
        )

    hedge_texto = f"{info.get('hipotese', '')} {hedge_explicacao}".strip()
    if info.get("nota"):
        hedge_texto += f" {info['nota']}"

    return {
        "titulo_hipotese": info.get("titulo", ""),
        "veredito_label": label,
        "zscore_texto": zscore_texto,
        "correlacao_texto": corr_texto,
        "cointegracao_texto": coint_texto,
        "hedge_ratio_texto": hedge_texto,
        "sintese": _forca_do_sinal(zscore, corr_atual, tendencia_corr, coint_pvalue),
    }
