def filter_deals(deals: list[dict], min_discount_rate: int) -> list[dict]:
    """할인율이 min_discount_rate 이상인 상품만 남긴다."""
    return [d for d in deals if d.get("discountRate", 0) >= min_discount_rate]
