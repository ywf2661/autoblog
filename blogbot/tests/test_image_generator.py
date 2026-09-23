import base64
from unittest.mock import MagicMock, patch

import requests

from config import Settings
from image_generator import (
    generate_image,
    insert_images,
    raw_image_url,
    save_generated_image,
)


def _settings(gemini_api_key="gk"):
    return Settings("ak", "gcid", "gcs", "grt", "blogid", gemini_api_key)


@patch("image_generator.requests.post")
def test_generate_image_returns_decoded_bytes(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"inlineData": {"data": base64.b64encode(b"pngdata").decode()}}
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    result = generate_image(_settings(), "노트북 삽화")

    assert result == b"pngdata"


@patch("image_generator.requests.post")
def test_generate_image_skips_request_when_key_missing(mock_post):
    result = generate_image(_settings(gemini_api_key=""), "노트북 삽화")

    assert result is None
    mock_post.assert_not_called()


@patch("image_generator.requests.post")
def test_generate_image_returns_none_on_request_error(mock_post):
    mock_post.side_effect = requests.RequestException("boom")

    result = generate_image(_settings(), "노트북 삽화")

    assert result is None


@patch("image_generator.requests.post")
def test_generate_image_returns_none_when_no_image_part(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "설명만 있음"}]}}]
    }
    mock_post.return_value = mock_response

    result = generate_image(_settings(), "노트북 삽화")

    assert result is None


def test_save_generated_image_writes_file(tmp_path):
    dir_path = tmp_path / "generated_images"

    path = save_generated_image(str(dir_path), "a.png", b"pngdata")

    with open(path, "rb") as f:
        assert f.read() == b"pngdata"


def test_raw_image_url_builds_github_raw_path():
    url = raw_image_url("generated_images", "a.png")

    assert url == (
        "https://raw.githubusercontent.com/ywf2661/autoblog/master/"
        "blogbot/generated_images/a.png"
    )


def test_insert_images_replaces_placeholders_with_img_tags():
    body = "<p>앞</p>[IMAGE_1]<p>중간</p>[IMAGE_2]<p>뒤</p>"

    result = insert_images(body, ["http://x/1.png", "http://x/2.png"])

    assert '<img src="http://x/1.png" alt="" style="max-width:100%">' in result
    assert '<img src="http://x/2.png" alt="" style="max-width:100%">' in result
    assert "[IMAGE_1]" not in result
    assert "[IMAGE_2]" not in result


def test_insert_images_removes_placeholder_when_url_is_none():
    body = "<p>앞</p>[IMAGE_1]<p>뒤</p>"

    result = insert_images(body, [None])

    assert result == "<p>앞</p><p>뒤</p>"
