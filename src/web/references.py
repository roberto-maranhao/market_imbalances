"""Bibliografia que embasa a metodologia do projeto — ver /metodologia e
src/web/interpretation.py (que cita estas chaves na leitura dinâmica de cada par)."""

REFERENCES: dict[str, dict[str, str]] = {
    "engle_granger_1987": {
        "citacao": (
            "Engle, R. F., & Granger, C. W. J. (1987). Co-integration and Error Correction: "
            "Representation, Estimation and Testing. Econometrica, 55(2), 251–276."
        ),
        "resumo": (
            "Formaliza o teste de cointegração de duas etapas que o statsmodels.tsa.stattools.coint "
            "(usado neste projeto) implementa: duas séries são cointegradas se existe uma combinação "
            "linear delas que é estacionária, mesmo que cada uma isoladamente não seja."
        ),
    },
    "gatev_2006": {
        "citacao": (
            "Gatev, E., Goetzmann, W. N., & Rouwenhorst, K. G. (2006). Pairs Trading: Performance "
            "of a Relative-Value Arbitrage Rule. Review of Financial Studies, 19(3), 797–827."
        ),
        "resumo": (
            "Estudo empírico seminal (dados de 1962–2002) que testa a estratégia de pares via "
            "'método da distância': retornos anualizados de até ~12% nos pares mais esticados, "
            "abrindo posição quando o spread diverge e fechando na reversão."
        ),
    },
    "vidyamurthy_2004": {
        "citacao": (
            "Vidyamurthy, G. (2004). Pairs Trading: Quantitative Methods and Analysis. Wiley."
        ),
        "resumo": (
            "Formaliza pairs trading via cointegração (não só distância) com regras de entrada/saída "
            "em unidades de desvio-padrão do spread — origem prática dos limiares |z|≥2 (abre) e "
            "|z|≤0.5 (normaliza) usados neste projeto."
        ),
    },
    "chan_2013": {
        "citacao": (
            "Chan, E. (2013). Algorithmic Trading: Winning Strategies and Their Rationale. Wiley."
        ),
        "resumo": (
            "Populariza o filtro de Kalman para hedge ratio dinâmico em pairs trading (vs. regressão "
            "OLS estática) — a relação entre dois ativos muda com o tempo, então um hedge ratio que "
            "se atualiza a cada observação captura isso melhor que um valor fixo por período."
        ),
    },
    "chen_rogoff_2003": {
        "citacao": (
            "Chen, Y., & Rogoff, K. (2003). Commodity Currencies. Journal of International "
            "Economics, 60(1), 133–160."
        ),
        "resumo": (
            "Mostra que o preço mundial da cesta de commodities exportadas é um driver robusto do "
            "câmbio real de moedas como AUD/CAD/NZD ('moedas-commodity') — base teórica (aplicada "
            "aqui por extensão ao BRL) para o par IC-Br vs. USDBRL."
        ),
    },
    "do_faff_2010": {
        "citacao": (
            "Do, B., & Faff, R. (2010). Does Simple Pairs Trading Still Work? Financial Analysts "
            "Journal, 66(4), 83–95."
        ),
        "resumo": (
            "Mostra que o retorno da estratégia clássica de pares caiu de ~0,86%/mês (1962–88) para "
            "~0,24%/mês (2003–09), atribuindo isso a 'risco de arbitragem' (risco fundamental, de "
            "noise trader, e de sincronização) — motivação direta para monitorar correlação móvel "
            "como alerta de quebra de regime, não só o z-score."
        ),
    },
}
