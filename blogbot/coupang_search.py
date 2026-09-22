import requests

from config import Settings
from signing import build_auth_header

BASE_URL = "https://api-gateway.coupang.com"
SEARCH_PATH = "/v2/providers/affiliate_open_api/apis/openapi/products/search"


def search_products(settings: Settings, keyword: str, limit: int = 3) -> list[dict]:
    """키워드로 쿠팡파트너스 상품을 검색한다. 실패하거나 결과가 없으면 빈 리스트를 반환."""
    query = f"keyword={keyword}&limit={limit}"
    headers = {
        "Authorization": build_auth_header(
            settings.coupang_access_key,
            settings.coupang_secret_key,
            "GET",
            SEARCH_PATH,
            query,
        ),
        "Content-Type": "application/json;charset=UTF-8",
    }
    try:
        response = requests.get(
            f"{BASE_URL}{SEARCH_PATH}?{query}", headers=headers, timeout=10
        )
        response.raise_for_status()
        products = response.json().get("data", {}).get("productData", [])
    except (requests.RequestException, ValueError, AttributeError, KeyError):
        return []

    return [
        {
            "productName": p.get("productName", ""),
            "productUrl": p.get("productUrl", ""),
            "productImage": p.get("productImage", ""),
            "productPrice": p.get("productPrice", 0),
        }
        for p in products[:limit]
    ]
