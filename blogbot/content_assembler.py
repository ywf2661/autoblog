import html


def assemble_post_html(body_html: str, products: list[dict]) -> str:
    """본문 HTML에 관련 상품 섹션을 덧붙인다. 상품이 없으면 본문만 반환."""
    if not products:
        return body_html

    items = "".join(
        f'<li><a href="{html.escape(p["productUrl"])}">{html.escape(p["productName"])}</a> - {p["productPrice"]:,}원</li>'
        for p in products
    )
    products_section = f"<h3>관련 상품</h3><ul>{items}</ul>"
    return f"{body_html}\n{products_section}"
