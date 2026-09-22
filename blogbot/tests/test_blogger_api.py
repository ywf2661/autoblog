from unittest.mock import MagicMock, patch

from config import Settings
from blogger_api import refresh_access_token, create_draft_post


def _settings():
    return Settings("ak", "cak", "csk", "gcid", "gcs", "grt", "12345")


@patch("blogger_api.requests.post")
def test_refresh_access_token_returns_token(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"access_token": "new-token"}
    mock_post.return_value = mock_response

    token = refresh_access_token(_settings())

    assert token == "new-token"


@patch("blogger_api.requests.post")
def test_create_draft_post_returns_edit_url(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"id": "999"}
    mock_post.return_value = mock_response

    url = create_draft_post(_settings(), "token", "제목", "<p>본문</p>")

    assert url == "https://www.blogger.com/blog/post/edit/12345/999"
    args, kwargs = mock_post.call_args
    assert kwargs["json"] == {"title": "제목", "content": "<p>본문</p>"}
    # Verify isDraft=true is in the request URL to prevent accidental live publishing
    assert "isDraft=true" in args[0]
