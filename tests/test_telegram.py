from unittest.mock import MagicMock, patch

from telegram import format_deal_message, send_telegram_message


def test_format_deal_message_includes_key_fields():
    deal = {
        "productName": "무선이어폰",
        "productPrice": 19900,
        "discountRate": 40,
        "productUrl": "http://x",
    }

    message = format_deal_message(deal)

    assert "40%" in message
    assert "무선이어폰" in message
    assert "19,900원" in message
    assert "http://x" in message


@patch("telegram.requests.post")
def test_send_telegram_message_calls_api_with_chat_id_and_text(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    send_telegram_message("TOKEN", "CHATID", "hello")

    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.telegram.org/botTOKEN/sendMessage"
    assert kwargs["json"] == {"chat_id": "CHATID", "text": "hello"}
