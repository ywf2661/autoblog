import time
from unittest.mock import MagicMock, patch

from rss_reader import fetch_feed_entries


@patch("rss_reader.feedparser.parse")
@patch("rss_reader.requests.get")
def test_fetch_feed_entries_returns_entries_with_published(mock_get, mock_parse):
    mock_response = MagicMock()
    mock_response.content = b"<rss></rss>"
    mock_get.return_value = mock_response

    mock_parsed = MagicMock()
    mock_parsed.bozo = False
    mock_parsed.entries = [
        {
            "title": "제목",
            "summary": "요약",
            "link": "http://x",
            "published_parsed": time.struct_time((2026, 9, 22, 0, 0, 0, 0, 0, 0)),
        }
    ]
    mock_parse.return_value = mock_parsed

    entries = fetch_feed_entries(["http://feed"])

    assert len(entries) == 1
    assert entries[0]["title"] == "제목"
    assert entries[0]["link"] == "http://x"
    mock_get.assert_called_once_with("http://feed", timeout=10)
    mock_parse.assert_called_once_with(mock_response.content)


@patch("rss_reader.feedparser.parse")
@patch("rss_reader.requests.get")
def test_fetch_feed_entries_skips_entry_without_published(mock_get, mock_parse):
    mock_response = MagicMock()
    mock_response.content = b"<rss></rss>"
    mock_get.return_value = mock_response

    mock_parsed = MagicMock()
    mock_parsed.bozo = False
    mock_parsed.entries = [{"title": "t", "summary": "s", "link": "l"}]
    mock_parse.return_value = mock_parsed

    entries = fetch_feed_entries(["http://feed"])

    assert entries == []


@patch("rss_reader.feedparser.parse")
@patch("rss_reader.requests.get")
def test_fetch_feed_entries_skips_broken_feed(mock_get, mock_parse):
    mock_response = MagicMock()
    mock_response.content = b"<rss></rss>"
    mock_get.return_value = mock_response

    mock_parsed = MagicMock()
    mock_parsed.bozo = True
    mock_parsed.entries = []
    mock_parse.return_value = mock_parsed

    entries = fetch_feed_entries(["http://broken-feed"])

    assert entries == []


@patch("rss_reader.feedparser.parse")
@patch("rss_reader.requests.get")
def test_fetch_feed_entries_continues_on_parse_error(mock_get, mock_parse):
    mock_response = MagicMock()
    mock_response.content = b"<rss></rss>"
    mock_get.return_value = mock_response

    mock_parsed = MagicMock()
    mock_parsed.bozo = False
    mock_parsed.entries = [
        {
            "title": "good entry",
            "summary": "s",
            "link": "http://y",
            "published_parsed": time.struct_time((2026, 9, 22, 0, 0, 0, 0, 0, 0)),
        }
    ]
    mock_parse.side_effect = [Exception("parse error"), mock_parsed]

    entries = fetch_feed_entries(["http://bad-feed", "http://good-feed"])

    assert len(entries) == 1
    assert entries[0]["title"] == "good entry"


@patch("rss_reader.requests.get")
def test_fetch_feed_entries_continues_on_request_timeout(mock_get):
    mock_response = MagicMock()
    mock_response.content = b"ok"
    mock_get.side_effect = [TimeoutError("timed out"), mock_response]

    with patch("rss_reader.feedparser.parse") as mock_parse:
        mock_parsed = MagicMock()
        mock_parsed.bozo = False
        mock_parsed.entries = [
            {
                "title": "good entry",
                "summary": "s",
                "link": "http://y",
                "published_parsed": time.struct_time((2026, 9, 22, 0, 0, 0, 0, 0, 0)),
            }
        ]
        mock_parse.return_value = mock_parsed

        entries = fetch_feed_entries(["http://slow-feed", "http://good-feed"])

    assert len(entries) == 1
    assert entries[0]["title"] == "good entry"
