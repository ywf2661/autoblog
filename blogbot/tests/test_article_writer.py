from unittest.mock import MagicMock, patch

import pytest

from config import Settings
from article_writer import write_article


def _settings():
    return Settings("ak", "cak", "csk", "gcid", "gcs", "grt", "blogid")


@patch("article_writer.requests.post")
def test_write_article_parses_json_response(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "content": [
            {
                "text": '{"title": "제목", "body_html": "<p>본문</p>", "keywords": ["노트북"]}'
            }
        ]
    }
    mock_post.return_value = mock_response

    result = write_article(
        _settings(), {"title": "t", "summary": "s", "link": "http://x"}
    )

    assert result["title"] == "제목"
    assert result["keywords"] == ["노트북"]


@patch("article_writer.requests.post")
def test_write_article_raises_on_invalid_json(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"content": [{"text": "이건 JSON이 아님"}]}
    mock_post.return_value = mock_response

    with pytest.raises(ValueError):
        write_article(_settings(), {"title": "t", "summary": "s", "link": "http://x"})


@patch("article_writer.requests.post")
def test_write_article_defaults_keywords_when_missing(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "content": [{"text": '{"title": "제목", "body_html": "<p>본문</p>"}'}]
    }
    mock_post.return_value = mock_response

    result = write_article(
        _settings(), {"title": "t", "summary": "s", "link": "http://x"}
    )

    assert result["keywords"] == []


@patch("article_writer.requests.post")
def test_write_article_raises_on_malformed_response_envelope(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"content": []}
    mock_post.return_value = mock_response

    with pytest.raises(ValueError):
        write_article(_settings(), {"title": "t", "summary": "s", "link": "http://x"})
