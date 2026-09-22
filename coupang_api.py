import requests

from config import Settings
from signing import build_auth_header

BASE_URL = "https://api-gateway.coupang.com"
GOLDBOX_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/goldbox"


def fetch_goldbox_deals(settings: Settings) -> list[dict]:
    """쿠팡파트너스 골드박스 특가 상품 목록 조회."""
    headers = {
        "Authorization": build_auth_header(
            settings.access_key, settings.secret_key, "GET", GOLDBOX_PATH
        ),
        "Content-Type": "application/json;charset=UTF-8",
    }
    response = requests.get(BASE_URL + GOLDBOX_PATH, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json().get("data", [])
    if isinstance(data, dict):
        return data.get("productData", [])
    if isinstance(data, list):
        return data
    return []
