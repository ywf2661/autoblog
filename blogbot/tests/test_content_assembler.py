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


def test_assemble_post_html_skips_section_when_no_products():
    html = assemble_post_html("<p>본문</p>", [])

    assert html == "<p>본문</p>"
