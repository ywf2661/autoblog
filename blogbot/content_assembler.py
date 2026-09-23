import html


def assemble_post_html(body_html: str, products: list[dict]) -> str:
    """본문 HTML에 관련 상품 섹션을 덧붙인다. 상품이 없으면 본문만 반환."""
    if not products:
        return body_html

    # ponytail: div+flex 대신 table을 쓰는 이유 — 티스토리 등 블로그 에디터가
    # 붙여넣기 시 style 속성을 걷어내는 경우가 많아 flex 레이아웃이 깨짐.
    # table/td는 구조 자체가 레이아웃이라 훨씬 안정적으로 살아남는다(이메일 HTML과 동일한 이유).
    width_pct = max(100 // len(products), 20)
    cells = "".join(
        f'<td align="center" valign="top" width="{width_pct}%">'
        f'<a href="{html.escape(p["productUrl"])}">'
        f'<img src="{html.escape(p["productImage"])}" alt="{html.escape(p["productName"])}" '
        'width="150" style="max-width:100%"><br>'
        f'{html.escape(p["productName"])}<br>'
        f'<font color="#e53935"><b>{p["productPrice"]:,}원</b></font>'
        "</a></td>"
        for p in products
    )
    disclosure = (
        '<p><small>이 포스팅은 쿠팡 파트너스 활동의 일환으로, '
        "이에 따른 일정액의 수수료를 제공받습니다.</small></p>"
    )
    products_section = (
        "<h3>관련 상품</h3>"
        f'<table width="100%" cellpadding="8"><tr>{cells}</tr></table>'
        f"{disclosure}"
    )
    return f"{body_html}\n{products_section}"
