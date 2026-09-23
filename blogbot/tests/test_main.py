from unittest.mock import mock_open, patch

import main


@patch("main.save_posted_ids")
@patch("main.create_draft_post")
@patch("main.refresh_access_token")
@patch("main.write_tistory_draft")
@patch("main.search_products")
@patch("main.insert_images")
@patch("main.generate_image")
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
    mock_generate_image,
    mock_insert_images,
    mock_search,
    mock_write_tistory,
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
        "image_prompts": [],
    }
    mock_search.return_value = []
    mock_insert_images.return_value = "<p>본문</p>"
    mock_refresh.return_value = "token"
    mock_create_draft.return_value = "http://blogger-edit-url"

    result = main.run()

    assert result == "http://blogger-edit-url"
    mock_save_posted.assert_called_once()
    mock_search.assert_called_once_with("노트북")
    mock_generate_image.assert_not_called()
    mock_write_tistory.assert_called_once()
    assert mock_write_tistory.call_args[0][2] == "제목"
    assert mock_write_tistory.call_args[0][3] == "<p>본문</p>"


@patch("main.save_posted_ids")
@patch("main.create_draft_post")
@patch("main.refresh_access_token")
@patch("main.write_tistory_draft")
@patch("main.search_products")
@patch("main.raw_image_url")
@patch("main.save_generated_image")
@patch("main.insert_images")
@patch("main.generate_image")
@patch("main.write_article")
@patch("main.load_posted_ids")
@patch("main.fetch_feed_entries")
@patch("main.load_settings")
@patch("builtins.open", new_callable=mock_open, read_data="http://feed1\n")
def test_run_generates_images_for_each_prompt_and_skips_failed_ones(
    mock_file,
    mock_load_settings,
    mock_fetch,
    mock_load_posted,
    mock_write_article,
    mock_generate_image,
    mock_insert_images,
    mock_save_image,
    mock_raw_url,
    mock_search,
    mock_write_tistory,
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
        "body_html": "<p>[IMAGE_1][IMAGE_2]</p>",
        "keywords": [],
        "image_prompts": ["프롬프트1", "프롬프트2"],
    }
    mock_generate_image.side_effect = [b"bytes1", None]
    mock_raw_url.return_value = "http://raw/1.png"
    mock_search.return_value = []
    mock_insert_images.return_value = "<p>본문</p>"
    mock_refresh.return_value = "token"
    mock_create_draft.return_value = "http://blogger-edit-url"

    main.run()

    assert mock_generate_image.call_count == 2
    mock_save_image.assert_called_once()
    mock_insert_images.assert_called_once_with(
        "<p>[IMAGE_1][IMAGE_2]</p>", ["http://raw/1.png", None]
    )


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
