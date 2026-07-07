from src.collectors.sources.edgar_source import _latest_usd_value


def make_facts(entries):
    return {"facts": {"us-gaap": {"PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": entries}}}}}


def test_latest_usd_value_picks_max_end_date():
    facts = make_facts(
        [
            {"end": "2025-06-30", "val": 10_000_000_000},
            {"end": "2026-06-30", "val": 15_000_000_000},
            {"end": "2024-06-30", "val": 8_000_000_000},
        ]
    )

    result = _latest_usd_value(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"])

    assert result == ("2026-06-30", 15_000_000_000.0)


def test_latest_usd_value_falls_back_to_second_tag():
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [{"end": "2026-03-31", "val": 5.0}]}}}}}

    result = _latest_usd_value(facts, ["MissingTag", "Revenues"])

    assert result == ("2026-03-31", 5.0)


def test_latest_usd_value_returns_none_when_no_tag_matches():
    facts = {"facts": {"us-gaap": {}}}

    assert _latest_usd_value(facts, ["MissingTag"]) is None


def test_latest_usd_value_prefers_newer_data_even_from_second_tag():
    """Empresas trocam de tag XBRL ao longo do tempo (ex: MSFT parou de usar 'Revenues' em
    ~2018). A primeira tag da lista pode ter dados antigos que não devem vencer dados mais
    recentes de uma tag posterior."""
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [{"end": "2010-12-31", "val": 1.0}]}},
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": [{"end": "2026-03-31", "val": 2.0}]}
                },
            }
        }
    }

    result = _latest_usd_value(facts, ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"])

    assert result == ("2026-03-31", 2.0)


def test_latest_usd_value_prefers_quarter_over_ttm_with_same_end_date():
    """A SEC às vezes reporta, para o mesmo 'end', tanto o trimestre isolado quanto um
    trailing-twelve-months (start bem mais antigo). Sem desambiguar, um TTM ~4x maior
    poderia ser confundido com o valor trimestral (caso real: capex da Amazon)."""
    facts = make_facts(
        [
            {"start": "2025-04-01", "end": "2026-03-31", "val": 151_003_000_000},  # TTM, sem frame
            {"start": "2026-01-01", "end": "2026-03-31", "val": 44_203_000_000, "frame": "CY2026Q1"},
        ]
    )

    result = _latest_usd_value(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"])

    assert result == ("2026-03-31", 44_203_000_000.0)
