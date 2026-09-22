import time

from config import load_settings
from coupang_api import fetch_goldbox_deals
from filters import filter_deals
from dedup import load_sent_ids, save_sent_ids, filter_unsent
from telegram import format_deal_message, send_telegram_message

SENT_IDS_PATH = "sent_ids.json"
MAX_SENDS_PER_RUN = 20
SEND_INTERVAL_SECONDS = 1


def run() -> int:
    """특가봇 1회 실행. 새로 전송한 상품 개수를 반환한다."""
    settings = load_settings()

    raw_deals = fetch_goldbox_deals(settings)
    filtered_deals = filter_deals(raw_deals, settings.min_discount_rate)

    sent_ids = load_sent_ids(SENT_IDS_PATH)
    new_deals = filter_unsent(filtered_deals, sent_ids)
    to_send = new_deals[:MAX_SENDS_PER_RUN]

    print(
        f"조회 {len(raw_deals)}건 → 할인율 통과 {len(filtered_deals)}건 → "
        f"신규 {len(new_deals)}건 → 이번 실행 전송 대상 {len(to_send)}건"
    )

    sent_count = 0
    try:
        for deal in to_send:
            message = format_deal_message(deal)
            send_telegram_message(settings.telegram_token, settings.telegram_chat_id, message)
            sent_ids[deal["productId"]] = None
            sent_count += 1
            if deal is not to_send[-1]:
                time.sleep(SEND_INTERVAL_SECONDS)
    finally:
        save_sent_ids(SENT_IDS_PATH, sent_ids)

    return sent_count


if __name__ == "__main__":
    count = run()
    print(f"전송 완료: {count}건")
