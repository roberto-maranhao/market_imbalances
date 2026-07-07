import datetime as dt
from unittest.mock import Mock, patch

import requests

from src.collectors.sources.bcb_source import fetch_range, fetch_series


class _BadJsonResponse:
    def raise_for_status(self):
        pass

    def json(self):
        raise ValueError("Expecting value: line 1 column 1 (char 0)")


def test_fetch_range_returns_empty_list_instead_of_raising_on_bad_json():
    """Bug real observado num backfill: o BCB às vezes responde HTTP 200 com corpo vazio/
    não-JSON. .json() estourava fora do try/except e derrubava o backfill inteiro."""
    with patch("src.collectors.sources.bcb_source.get_with_retry", return_value=_BadJsonResponse()):
        result = fetch_range("USDBRL_PTAX", 1, dt.date(2020, 1, 1), dt.date(2020, 12, 31))

    assert result == []


def test_fetch_series_returns_empty_list_instead_of_raising_on_bad_json():
    with patch("src.collectors.sources.bcb_source.get_with_retry", return_value=_BadJsonResponse()):
        result = fetch_series("IC_BR", 27574)

    assert result == []


def test_fetch_range_treats_404_as_no_data_not_an_error():
    """Observado num backfill real: paginar em blocos de anos pode deixar um último pedaço
    de janela sem nenhum ponto (comum em séries mensais) — o BCB responde 404 nesse caso,
    não uma lista vazia. Isso é 'sem dados', não uma falha a interromper o backfill."""
    response = Mock()
    error = requests.HTTPError(response=Mock(status_code=404))
    with patch("src.collectors.sources.bcb_source.get_with_retry", side_effect=error):
        result = fetch_range("IC_BR", 27574, dt.date(2026, 7, 4), dt.date(2026, 7, 7))

    assert result == []


def test_fetch_series_parses_valid_response():
    mock_resp = Mock()
    mock_resp.json.return_value = [{"data": "01/07/2026", "valor": "5.15"}]
    with patch("src.collectors.sources.bcb_source.get_with_retry", return_value=mock_resp):
        result = fetch_series("USDBRL_PTAX", 1)

    assert len(result) == 1
    assert result[0].preco == 5.15
