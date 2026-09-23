import html


def assemble_post_html(body_html: str, products: list[dict]) -> str:
    """본문 HTML에 관련 상품 섹션을 덧붙인다. 상품이 없으면 본문만 반환."""
    if not products:
        return body_html

    cards = "".join(
        '<div style="flex:1 1 140px;max-width:180px;border:1px solid #e5e5e5;'
        'border-radius:10px;padding:12px;text-align:center;">'
        f'<a href="{html.escape(p["productUrl"])}" '
        'style="text-decoration:none;color:inherit;display:block;">'
        f'<img src="{html.escape(p["productImage"])}" alt="{html.escape(p["productName"])}" '
        'style="width:100%;max-width:150px;border-radius:6px;">'
        '<div style="margin-top:8px;font-size:14px;line-height:1.4;">'
        f'{html.escape(p["productName"])}</div>'
        '<div style="margin-top:6px;font-weight:bold;color:#e53935;">'
        f'{p["productPrice"]:,}원</div>'
        "</a></div>"
        for p in products
    )
    disclosure = (
        '<p><small>이 포스팅은 쿠팡 파트너스 활동의 일환으로, '
        "이에 따른 일정액의 수수료를 제공받습니다.</small></p>"
    )
    products_section = (
        "<h3>관련 상품</h3>"
        f'<div style="display:flex;flex-wrap:wrap;gap:12px;margin:12px 0;">{cards}</div>'
        f"{disclosure}"
    )
    return f"{body_html}\n{products_section}"
