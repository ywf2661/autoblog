from config import load_settings
from coupang_api import fetch_goldbox_deals
from filters import filter_deals
from dedup import load_sent_ids, save_sent_ids, filter_unsent
from telegram import format_deal_message, send_telegram_message

SENT_IDS_PATH = "sent_ids.json"


def run() -> int:
    """특가봇 1회 실행. 새로 전송한 상품 개수를 반환한다."""
    settings = load_settings()

    deals = fetch_goldbox_deals(settings)
    deals = filter_deals(deals, settings.min_discount_rate)

    sent_ids = load_sent_ids(SENT_IDS_PATH)
    new_deals = filter_unsent(deals, sent_ids)

    for deal in new_deals:
        message = format_deal_message(deal)
        send_telegram_message(settings.telegram_token, settings.telegram_chat_id, message)
        sent_ids[deal["productId"]] = None

    save_sent_ids(SENT_IDS_PATH, sent_ids)
    return len(new_deals)


if __name__ == "__main__":
    count = run()
    print(f"전송 완료: {count}건")
