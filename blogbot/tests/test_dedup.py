import json
import time

from dedup import hash_link, load_posted_ids, save_posted_ids, pick_next_entry, MAX_HISTORY


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


def test_save_posted_ids_trims_oldest_when_exceeding_max_history(tmp_path):
    """Verify that MAX_HISTORY trimming keeps newest entries, not arbitrary ones.

    When saved entries exceed MAX_HISTORY (500), oldest entries from the prior
    on-disk order are trimmed, preserving recency.
    """
    path = str(tmp_path / "posted.json")

    # Step 1: Create an initial file with 510 entries in known order (oldest first)
    initial_entries = [f"id_{i}" for i in range(510)]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(initial_entries, f)

    # Step 2: Simulate a save with some entries pruned (0-9 removed) and 5 new ones added
    # This creates 505 entries (500 retained + 5 new), which exceeds MAX_HISTORY
    existing_ids = set(initial_entries[10:510])  # Keep id_10 to id_509
    new_ids = {"new_0", "new_1", "new_2", "new_3", "new_4"}
    all_ids = existing_ids | new_ids

    # Step 3: Save with the new set (505 entries → trim to 500)
    save_posted_ids(path, all_ids)

    # Step 4: Load and verify
    result = load_posted_ids(path)

    # Should have exactly MAX_HISTORY entries (trimmed from 505 to 500)
    assert len(result) == MAX_HISTORY

    # Should NOT contain entries trimmed from the front (oldest 5 of the kept entries)
    # id_10 through id_14 should be trimmed
    assert "id_0" not in result    # Never in the input
    assert "id_9" not in result    # Never in the input
    assert "id_10" not in result   # Trimmed to make room (oldest of kept entries)
    assert "id_14" not in result   # Trimmed to make room

    # Should contain entries that survived the trim
    assert "id_15" in result       # First entry after trim
    assert "id_509" in result      # Last entry before new ones

    # Should contain all new entries
    assert new_ids.issubset(result)
