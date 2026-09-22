from content_assembler import assemble_post_html


def test_assemble_post_html_appends_products_section():
    html = assemble_post_html(
        "<p>본문</p>",
        [
            {
                "productName": "노트북",
                "productUrl": "http://x",
                "productImage": "",
                "productPrice": 1000000,
            }
        ],
    )

    assert "<p>본문</p>" in html
    assert "노트북" in html
    assert "1,000,000원" in html
    assert "쿠팡 파트너스 활동의 일환으로" in html


def test_assemble_post_html_skips_section_when_no_products():
    html = assemble_post_html("<p>본문</p>", [])

    assert html == "<p>본문</p>"
    assert "쿠팡 파트너스" not in html


def test_assemble_post_html_escapes_special_characters():
    html = assemble_post_html(
        "<p>본문</p>",
        [
            {
                "productName": "A&W <Best>",
                "productUrl": "http://example.com?a=1&b=2",
                "productImage": "",
                "productPrice": 5000,
            }
        ],
    )

    assert "A&amp;W &lt;Best&gt;" in html
    assert "http://example.com?a=1&amp;b=2" in html
    assert '<li><a href="http://example.com?a=1&amp;b=2">A&amp;W &lt;Best&gt;</a> - 5,000원</li>' in html
