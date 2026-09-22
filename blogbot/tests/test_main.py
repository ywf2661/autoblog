from unittest.mock import mock_open, patch

import main


@patch("main.save_posted_ids")
@patch("main.create_draft_post")
@patch("main.refresh_access_token")
@patch("main.search_products")
@patch("main.write_article")
@patch("main.load_posted_ids")
@patch("main.fetch_feed_entries")
@patch("main.load_settings")
@patch("builtins.open", new_callable=mock_open, read_data="http://feed1\nhttp://feed2\n")
def test_run_creates_draft_for_next_entry(
    mock_file,
    mock_load_settings,
    mock_fetch,
    mock_load_posted,
    mock_write_article,
    mock_search,
    mock_refresh,
    mock_create_draft,
    mock_save_posted,
):
    mock_load_settings.return_value = object()
    mock_fetch.return_value = [
        {"title": "t", "summary": "s", "link": "http://x", "published": (2026, 9, 22)}
    ]
    mock_load_posted.return_value = set()
    mock_write_article.return_value = {
        "title": "제목",
        "body_html": "<p>본문</p>",
        "keywords": ["노트북"],
    }
    mock_search.return_value = []
    mock_refresh.return_value = "token"
    mock_create_draft.return_value = "http://blogger-edit-url"

    result = main.run()

    assert result == "http://blogger-edit-url"
    mock_save_posted.assert_called_once()
    mock_search.assert_called_once_with(mock_load_settings.return_value, "노트북")


@patch("main.load_posted_ids")
@patch("main.fetch_feed_entries")
@patch("main.load_settings")
@patch("builtins.open", new_callable=mock_open, read_data="http://feed1\n")
def test_run_returns_none_when_no_new_entry(
    mock_file, mock_load_settings, mock_fetch, mock_load_posted
):
    mock_load_settings.return_value = object()
    mock_fetch.return_value = []
    mock_load_posted.return_value = set()

    result = main.run()

    assert result is None
