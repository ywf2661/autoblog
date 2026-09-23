import os
import sys

_SHORTSBOT_DIR = os.path.dirname(os.path.abspath(__file__))
BLOGBOT_DIR = os.path.join(os.path.dirname(_SHORTSBOT_DIR), "blogbot")
if BLOGBOT_DIR not in sys.path:
    sys.path.append(BLOGBOT_DIR)

from rss_reader import fetch_feed_entries  # noqa: E402
from image_generator import generate_image, save_generated_image  # noqa: E402
from dedup import hash_link, load_posted_ids, save_posted_ids  # noqa: E402
import coupang_search as _coupang_search  # noqa: E402

_coupang_search.CURATED_PRODUCTS_PATH = os.path.join(BLOGBOT_DIR, "curated_products.json")


def search_products(keyword: str, limit: int = 3) -> list[dict]:
    """blogbot의 curated_products.json을 기준으로 관련상품을 조회한다."""
    return _coupang_search.search_products(keyword, limit)
