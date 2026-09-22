from unittest.mock import MagicMock, patch
from urllib.parse import quote_plus

import requests

from config import Settings
from coupang_search import search_products


def _settings():
    return Settings("ak", "cak", "csk", "gcid", "gcs", "grt", "blogid")


@patch("coupang_search.requests.get")
def test_search_products_returns_product_list(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "data": {
            "productData": [
                {
                    "productName": "노트북",
                    "productUrl": "http://x",
                    "productImage": "http://img",
                    "productPrice": 1000000,
                }
            ]
        }
    }
    mock_get.return_value = mock_response

    result = search_products(_settings(), "노트북")

    assert len(result) == 1
    assert result[0]["productName"] == "노트북"


@patch("coupang_search.requests.get")
def test_search_products_returns_empty_list_on_request_error(mock_get):
    mock_get.side_effect = requests.RequestException("boom")

    result = search_products(_settings(), "노트북")

    assert result == []


@patch("coupang_search.requests.get")
def test_search_products_encodes_keyword_in_request_url(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"data": {"productData": []}}
    mock_get.return_value = mock_response

    keyword = "블루투스 이어폰"
    search_products(_settings(), keyword)

    called_url = mock_get.call_args[0][0]
    assert quote_plus(keyword) in called_url
    assert keyword not in called_url


@patch("coupang_search.requests.get")
def test_search_products_skips_request_when_keys_missing(mock_get):
    settings = Settings("ak", "", "", "gcid", "gcs", "grt", "blogid")

    result = search_products(settings, "노트북")

    assert result == []
    mock_get.assert_not_called()


@patch("coupang_search.requests.get")
def test_search_products_returns_empty_list_on_malformed_json(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = ValueError("bad json")
    mock_get.return_value = mock_response

    result = search_products(_settings(), "노트북")

    assert result == []
