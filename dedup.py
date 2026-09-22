import json
import os

MAX_HISTORY = 500


def load_sent_ids(path: str) -> dict[int, None]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return {pid: None for pid in json.load(f)}


def save_sent_ids(path: str, sent_ids: dict[int, None]) -> None:
    trimmed = list(sent_ids.keys())[-MAX_HISTORY:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trimmed, f)


def filter_unsent(deals: list[dict], sent_ids: dict[int, None]) -> list[dict]:
    return [d for d in deals if d["productId"] not in sent_ids]
