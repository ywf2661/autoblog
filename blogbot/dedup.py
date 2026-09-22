import hashlib
import json
import os

MAX_HISTORY = 500


def hash_link(link: str) -> str:
    return hashlib.sha256(link.encode("utf-8")).hexdigest()


def load_posted_ids(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_posted_ids(path: str, ids: set[str]) -> None:
    trimmed = list(ids)[-MAX_HISTORY:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trimmed, f)


def pick_next_entry(entries: list[dict], posted_ids: set[str]) -> dict | None:
    """미게시 항목 중 published가 가장 최신인 1건을 반환한다."""
    unposted = [e for e in entries if hash_link(e["link"]) not in posted_ids]
    if not unposted:
        return None
    return max(unposted, key=lambda e: e["published"])
