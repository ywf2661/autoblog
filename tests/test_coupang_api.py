from unittest.mock import MagicMock, patch

import pytest

from config import Settings
from coupang_api import fetch_goldbox_deals


@patch("coupang_api.requests.get")
def test_fetch_goldbox_deals_returns_product_list(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "productData": [
                {
                    "productId": 1,
                    "productName": "test",
                    "productPrice": 1000,
                    "productUrl": "http://x",
                    "discountRate": 50,
                }
            ]
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    settings = Settings("ak", "sk", "tt", "cid")
    deals = fetch_goldbox_deals(settings)

    assert len(deals) == 1
    assert deals[0]["productId"] == 1


@patch("coupang_api.requests.get")
def test_fetch_goldbox_deals_raises_on_http_error(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = RuntimeError("HTTP 500")
    mock_get.return_value = mock_response

    settings = Settings("ak", "sk", "tt", "cid")

    with pytest.raises(RuntimeError):
        fetch_goldbox_deals(settings)
