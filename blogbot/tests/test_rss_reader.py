import time
from unittest.mock import MagicMock, patch

from rss_reader import fetch_feed_entries


@patch("rss_reader.feedparser.parse")
def test_fetch_feed_entries_returns_entries_with_published(mock_parse):
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


@patch("rss_reader.feedparser.parse")
def test_fetch_feed_entries_skips_entry_without_published(mock_parse):
    mock_parsed = MagicMock()
    mock_parsed.bozo = False
    mock_parsed.entries = [{"title": "t", "summary": "s", "link": "l"}]
    mock_parse.return_value = mock_parsed

    entries = fetch_feed_entries(["http://feed"])

    assert entries == []


@patch("rss_reader.feedparser.parse")
def test_fetch_feed_entries_skips_broken_feed(mock_parse):
    mock_parsed = MagicMock()
    mock_parsed.bozo = True
    mock_parsed.entries = []
    mock_parse.return_value = mock_parsed

    entries = fetch_feed_entries(["http://broken-feed"])

    assert entries == []


@patch("rss_reader.feedparser.parse")
def test_fetch_feed_entries_continues_on_parse_error(mock_parse):
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
