import json
import sys

import blogbot_bridge


def test_blogbot_dir_is_sibling_of_shortsbot_and_on_syspath():
    assert blogbot_bridge.BLOGBOT_DIR.endswith("blogbot")
    assert blogbot_bridge.BLOGBOT_DIR in sys.path


def test_reexports_blogbot_functions():
    assert callable(blogbot_bridge.fetch_feed_entries)
    assert callable(blogbot_bridge.generate_image)
    assert callable(blogbot_bridge.save_generated_image)
    assert callable(blogbot_bridge.hash_link)
    assert callable(blogbot_bridge.load_posted_ids)
    assert callable(blogbot_bridge.save_posted_ids)


def test_search_products_reads_blogbot_curated_catalog(tmp_path, monkeypatch):
    catalog_path = tmp_path / "curated_products.json"
    catalog_path.write_text(
        json.dumps(
            {
                "노트북": [
                    {
                        "productName": "노트북 A",
                        "productUrl": "http://x",
                        "productImage": "http://img",
                        "productPrice": 1000000,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        blogbot_bridge._coupang_search, "CURATED_PRODUCTS_PATH", str(catalog_path)
    )

    result = blogbot_bridge.search_products("최신 노트북 추천")

    assert len(result) == 1
    assert result[0]["productName"] == "노트북 A"
