import time

from dedup import hash_link, load_posted_ids, save_posted_ids, pick_next_entry


def test_load_posted_ids_returns_empty_set_when_file_missing():
    assert load_posted_ids("/tmp/does-not-exist-blogbot.json") == set()


def test_save_and_load_round_trip(tmp_path):
    path = str(tmp_path / "posted.json")
    save_posted_ids(path, {"aaa", "bbb"})

    result = load_posted_ids(path)

    assert result == {"aaa", "bbb"}


def test_pick_next_entry_picks_latest_unposted():
    old = time.struct_time((2026, 9, 20, 0, 0, 0, 0, 0, 0))
    new = time.struct_time((2026, 9, 22, 0, 0, 0, 0, 0, 0))
    entries = [
        {"link": "http://a", "published": old},
        {"link": "http://b", "published": new},
    ]

    result = pick_next_entry(entries, posted_ids=set())

    assert result["link"] == "http://b"


def test_pick_next_entry_returns_none_when_all_posted():
    entry = {
        "link": "http://a",
        "published": time.struct_time((2026, 9, 20, 0, 0, 0, 0, 0, 0)),
    }

    result = pick_next_entry([entry], posted_ids={hash_link("http://a")})

    assert result is None
