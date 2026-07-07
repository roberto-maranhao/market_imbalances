from src.collectors.sources.edgar_source import _all_framed_values, _latest_usd_value


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


def test_all_framed_values_only_keeps_frame_tagged_entries_sorted_by_end():
    facts = make_facts(
        [
            {"start": "2025-01-01", "end": "2025-03-31", "val": 10.0, "frame": "CY2025Q1"},
            {"start": "2024-04-01", "end": "2025-03-31", "val": 40.0},  # TTM sem frame, deve ser ignorado
            {"start": "2025-04-01", "end": "2025-06-30", "val": 12.0, "frame": "CY2025Q2"},
        ]
    )

    result = _all_framed_values(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"])

    assert result == [("2025-03-31", 10.0), ("2025-06-30", 12.0)]


def test_all_framed_values_merges_across_tags_without_overwriting_first_match():
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {"USD": [{"start": "2017-01-01", "end": "2017-03-31", "val": 5.0, "frame": "CY2017Q1"}]}
                },
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": [{"start": "2026-01-01", "end": "2026-03-31", "val": 9.0, "frame": "CY2026Q1"}]}
                },
            }
        }
    }

    result = _all_framed_values(facts, ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"])

    assert result == [("2017-03-31", 5.0), ("2026-03-31", 9.0)]


def test_all_framed_values_excludes_annual_frame_at_same_end_as_q4():
    """Caso real observado no capex da Amazon: a SEC marca o 10-K anual com frame 'CY2013'
    (sem 'Qn') no MESMO 'end' de 31/dez que o Q4 usaria — sem filtrar, o total anual
    (~4x maior) some junto com os trimestres na série, distorcendo qualquer índice
    calculado sobre ela."""
    facts = make_facts(
        [
            {"start": "2013-01-01", "end": "2013-03-31", "val": 670.0, "frame": "CY2013Q1"},
            {"start": "2013-04-01", "end": "2013-06-30", "val": 855.0, "frame": "CY2013Q2"},
            {"start": "2013-07-01", "end": "2013-09-30", "val": 1038.0, "frame": "CY2013Q3"},
            {"start": "2013-01-01", "end": "2013-12-31", "val": 3444.0, "frame": "CY2013"},  # ANUAL, não Q4
        ]
    )

    result = _all_framed_values(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"])

    assert result == [("2013-03-31", 670.0), ("2013-06-30", 855.0), ("2013-09-30", 1038.0)]
