import requests


def format_deal_message(deal: dict) -> str:
    name = deal.get("productName", "상품")
    price = deal.get("productPrice", 0)
    discount = deal.get("discountRate", 0)
    url = deal.get("productUrl", "")
    return f"🔥 {discount}% 할인\n{name}\n{price:,}원\n{url}"


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    response.raise_for_status()
