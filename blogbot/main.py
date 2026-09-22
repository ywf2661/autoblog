from article_writer import write_article
from blogger_api import create_draft_post, refresh_access_token
from config import load_settings
from content_assembler import assemble_post_html
from coupang_search import search_products
from dedup import hash_link, load_posted_ids, pick_next_entry, save_posted_ids
from rss_reader import fetch_feed_entries

FEEDS_PATH = "feeds.txt"
POSTED_IDS_PATH = "posted_ids.json"


def _load_feed_urls(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def run() -> str | None:
    """블로그봇 1회 실행. 새 draft를 만들었으면 편집 URL, 아니면 None."""
    settings = load_settings()

    feed_urls = _load_feed_urls(FEEDS_PATH)
    entries = fetch_feed_entries(feed_urls)
    if not entries:
        print(f"수집된 기사가 없습니다 (피드 {len(feed_urls)}개 모두 실패했을 수 있음).")
        return None

    posted_ids = load_posted_ids(POSTED_IDS_PATH)
    entry = pick_next_entry(entries, posted_ids)
    if entry is None:
        print(f"기사 {len(entries)}건을 수집했지만 새로운 기사가 없습니다.")
        return None

    article = write_article(settings, entry)

    keywords = article.get("keywords", [])
    products = search_products(keywords[0]) if keywords else []

    html = assemble_post_html(article["body_html"], products)

    access_token = refresh_access_token(settings)
    edit_url = create_draft_post(settings, access_token, article["title"], html)

    posted_ids.add(hash_link(entry["link"]))
    save_posted_ids(POSTED_IDS_PATH, posted_ids)

    return edit_url


if __name__ == "__main__":
    result = run()
    if result:
        print(f"초안 생성 완료: {result}")
    else:
        print("새로 게시할 기사가 없습니다.")
