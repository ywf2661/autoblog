import os
import tempfile

from dedup import load_sent_ids, save_sent_ids, filter_unsent


def test_load_sent_ids_returns_empty_set_when_file_missing():
    assert load_sent_ids("/tmp/does-not-exist-xyz.json") == set()


def test_save_and_load_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sent.json")
        save_sent_ids(path, {1, 2, 3})

        result = load_sent_ids(path)

        assert result == {1, 2, 3}


def test_filter_unsent_excludes_already_sent():
    deals = [{"productId": 1}, {"productId": 2}]

    result = filter_unsent(deals, sent_ids={1})

    assert result == [{"productId": 2}]
