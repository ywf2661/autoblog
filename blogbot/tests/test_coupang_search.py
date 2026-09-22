from unittest.mock import MagicMock, patch

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
