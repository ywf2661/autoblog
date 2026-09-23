import html


def assemble_post_html(body_html: str, products: list[dict]) -> str:
    """본문 HTML에 관련 상품 섹션을 덧붙인다. 상품이 없으면 본문만 반환."""
    if not products:
        return body_html

    items = "".join(
        f'<li><a href="{html.escape(p["productUrl"])}">'
        f'<img src="{html.escape(p["productImage"])}" alt="{html.escape(p["productName"])}" style="max-width:200px"><br>'
        f'{html.escape(p["productName"])}</a> - {p["productPrice"]:,}원</li>'
        for p in products
    )
    disclosure = (
        '<p><small>이 포스팅은 쿠팡 파트너스 활동의 일환으로, '
        "이에 따른 일정액의 수수료를 제공받습니다.</small></p>"
    )
    products_section = f"<h3>관련 상품</h3><ul>{items}</ul>{disclosure}"
    return f"{body_html}\n{products_section}"
