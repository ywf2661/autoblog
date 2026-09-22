import json

import coupang_search
from coupang_search import search_products


def _write_catalog(tmp_path, monkeypatch, catalog):
    path = tmp_path / "curated_products.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    monkeypatch.setattr(coupang_search, "CURATED_PRODUCTS_PATH", str(path))


def test_search_products_matches_category_by_substring(tmp_path, monkeypatch):
    _write_catalog(
        tmp_path,
        monkeypatch,
        {"노트북": [{"productName": "노트북 A", "productUrl": "http://x",
                    "productImage": "http://img", "productPrice": 1000000}]},
    )

    result = search_products("최신 노트북 추천")

    assert len(result) == 1
    assert result[0]["productName"] == "노트북 A"


def test_search_products_falls_back_to_default_category(tmp_path, monkeypatch):
    _write_catalog(
        tmp_path,
        monkeypatch,
        {
            "노트북": [{"productName": "노트북 A", "productUrl": "http://x",
                        "productImage": "http://img", "productPrice": 1000000}],
            "기본": [{"productName": "기본상품", "productUrl": "http://y",
                     "productImage": "http://img2", "productPrice": 5000}],
        },
    )

    result = search_products("전혀 매칭 안 되는 키워드")

    assert len(result) == 1
    assert result[0]["productName"] == "기본상품"


def test_search_products_returns_empty_when_no_match_and_no_default(tmp_path, monkeypatch):
    _write_catalog(tmp_path, monkeypatch, {"노트북": []})

    result = search_products("전혀 매칭 안 되는 키워드")

    assert result == []


def test_search_products_returns_empty_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        coupang_search, "CURATED_PRODUCTS_PATH", str(tmp_path / "missing.json")
    )

    result = search_products("노트북")

    assert result == []


def test_search_products_respects_limit(tmp_path, monkeypatch):
    products = [
        {"productName": f"상품{i}", "productUrl": "http://x",
         "productImage": "http://img", "productPrice": 1000}
        for i in range(5)
    ]
    _write_catalog(tmp_path, monkeypatch, {"이어폰": products})

    result = search_products("블루투스 이어폰", limit=2)

    assert len(result) == 2
