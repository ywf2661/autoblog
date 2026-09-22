import json
import os

MAX_HISTORY = 500


def load_sent_ids(path: str) -> set[int]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_sent_ids(path: str, sent_ids: set[int]) -> None:
    trimmed = list(sent_ids)[-MAX_HISTORY:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trimmed, f)


def filter_unsent(deals: list[dict], sent_ids: set[int]) -> list[dict]:
    return [d for d in deals if d["productId"] not in sent_ids]
