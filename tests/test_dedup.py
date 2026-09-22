import os
import tempfile

from dedup import load_sent_ids, save_sent_ids, filter_unsent


def test_load_sent_ids_returns_empty_set_when_file_missing():
    assert load_sent_ids("/tmp/does-not-exist-xyz.json") == {}


def test_save_and_load_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sent.json")
        save_sent_ids(path, {1: None, 2: None, 3: None})

        result = load_sent_ids(path)

        assert result == {1: None, 2: None, 3: None}


def test_filter_unsent_excludes_already_sent():
    deals = [{"productId": 1}, {"productId": 2}]

    result = filter_unsent(deals, sent_ids={1: None})

    assert result == [{"productId": 2}]


def test_save_sent_ids_trims_oldest_first():
    import dedup
    original_max = dedup.MAX_HISTORY
    dedup.MAX_HISTORY = 3
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sent.json")
            save_sent_ids(path, {1: None, 2: None, 3: None, 4: None, 5: None})
            result = load_sent_ids(path)
            assert list(result) == [3, 4, 5]
    finally:
        dedup.MAX_HISTORY = original_max
