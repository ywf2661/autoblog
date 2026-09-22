from filters import filter_deals


def test_filter_deals_keeps_only_high_discount():
    deals = [
        {"productId": 1, "discountRate": 50},
        {"productId": 2, "discountRate": 10},
        {"productId": 3, "discountRate": 30},
    ]

    result = filter_deals(deals, min_discount_rate=30)

    assert [d["productId"] for d in result] == [1, 3]


def test_filter_deals_treats_missing_rate_as_zero():
    deals = [{"productId": 1}]

    result = filter_deals(deals, min_discount_rate=1)

    assert result == []
