"""Nome legível, descrição e origem de cada ticker rastreado — usado para a dica (tooltip)
ao passar o mouse sobre um ticker na interface, sem trocar o texto exibido (ver plan.json ->
data_sources para o detalhe completo de cada fonte)."""

TICKER_INFO: dict[str, dict[str, str]] = {
    "BZ=F": {
        "nome": "Brent Crude",
        "descricao": "Futuro de petróleo Brent, referência internacional (Mar do Norte).",
        "fonte": "Yahoo Finance",
    },
    "PETR4.SA": {
        "nome": "Petrobras PN",
        "descricao": "Ação preferencial da Petrobras (PN: sem direito a voto, prioridade em dividendos), negociada na B3.",
        "fonte": "Yahoo Finance",
    },
    "TIO=F": {
        "nome": "Minério de Ferro 62% Fe",
        "descricao": "Futuro de minério de ferro (fino, 62% Fe), negociado na Singapore Exchange.",
        "fonte": "Yahoo Finance",
    },
    "VALE3.SA": {
        "nome": "Vale ON",
        "descricao": "Ação ordinária da Vale, maior produtora de minério de ferro do Brasil, negociada na B3.",
        "fonte": "Yahoo Finance",
    },
    "DX-Y.NYB": {
        "nome": "Índice DXY",
        "descricao": "Índice do dólar americano: cesta ponderada do USD contra EUR, JPY, GBP, CAD, SEK e CHF.",
        "fonte": "Yahoo Finance",
    },
    "BBDC3.SA": {
        "nome": "Bradesco ON",
        "descricao": "Ação ordinária do Bradesco (ON: com direito a voto), negociada na B3.",
        "fonte": "Yahoo Finance",
    },
    "BBDC4.SA": {
        "nome": "Bradesco PN",
        "descricao": "Ação preferencial do Bradesco (PN: sem direito a voto, prioridade em dividendos), negociada na B3.",
        "fonte": "Yahoo Finance",
    },
    "IC_BR": {
        "nome": "Índice de Commodities – Brasil",
        "descricao": "Índice de preços de commodities relevantes para a economia brasileira.",
        "fonte": "Banco Central do Brasil (SGS)",
    },
    "ITCR_BR": {
        "nome": "Índice da Taxa de Câmbio Real",
        "descricao": "Câmbio efetivo real do Real frente a uma cesta de moedas, ajustado pela inflação relativa (IREER).",
        "fonte": "Banco Central do Brasil (SGS)",
    },
    "USDBRL_PTAX": {
        "nome": "Dólar/Real (PTAX)",
        "descricao": "Taxa de câmbio oficial de referência USD/BRL, apurada diariamente pelo Banco Central.",
        "fonte": "Banco Central do Brasil (SGS/PTAX)",
    },
    "NVDA": {
        "nome": "Nvidia",
        "descricao": "Fabricante de GPUs e chips especializados para treinamento/inferência de IA.",
        "fonte": "Yahoo Finance",
    },
    "SMH": {
        "nome": "ETF de Semicondutores (VanEck)",
        "descricao": "ETF que replica um índice de empresas do setor de semicondutores.",
        "fonte": "Yahoo Finance",
    },
    "CRWV": {
        "nome": "CoreWeave",
        "descricao": "Provedora de infraestrutura de nuvem especializada em GPU para cargas de IA.",
        "fonte": "Yahoo Finance",
    },
    "DLR": {
        "nome": "Digital Realty",
        "descricao": "REIT (fundo imobiliário) de data centers.",
        "fonte": "Yahoo Finance",
    },
    "EQIX": {
        "nome": "Equinix",
        "descricao": "REIT de data centers e interconexão.",
        "fonte": "Yahoo Finance",
    },
    "SPCX": {
        "nome": "SpaceX",
        "descricao": "Ação da SpaceX, negociada publicamente desde o IPO em 12/06/2026.",
        "fonte": "Yahoo Finance",
    },
    "RKLB": {
        "nome": "Rocket Lab",
        "descricao": "Empresa de lançamento espacial e componentes de satélite.",
        "fonte": "Yahoo Finance",
    },
}

_HYPERSCALER_NAMES = {
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet (Google)",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "NVDA": "Nvidia",
    "ORCL": "Oracle",
}
for _ticker, _nome in _HYPERSCALER_NAMES.items():
    TICKER_INFO.setdefault(_ticker, {
        "nome": _nome,
        "descricao": "Hyperscaler monitorado no case study de capex de IA (capex e receita trimestrais).",
        "fonte": "SEC EDGAR (10-Q/10-K)",
    })
    TICKER_INFO[f"{_ticker}_CAPEX"] = {
        "nome": f"{_nome} — capex trimestral",
        "descricao": "Investimento em ativos fixos (capex) reportado no trimestre.",
        "fonte": "SEC EDGAR (10-Q/10-K)",
    }
    TICKER_INFO[f"{_ticker}_REVENUE"] = {
        "nome": f"{_nome} — receita trimestral",
        "descricao": "Receita total reportada no trimestre.",
        "fonte": "SEC EDGAR (10-Q/10-K)",
    }


def ticker_info(ticker: str) -> dict[str, str] | None:
    return TICKER_INFO.get(ticker)
