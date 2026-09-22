from unittest.mock import patch

import main


@patch("main.send_telegram_message")
@patch("main.save_sent_ids")
@patch("main.load_sent_ids")
@patch("main.fetch_goldbox_deals")
@patch("main.load_settings")
def test_run_sends_only_new_high_discount_deals(
    mock_load_settings, mock_fetch, mock_load_sent, mock_save_sent, mock_send
):
    mock_load_settings.return_value = type(
        "S", (), {"min_discount_rate": 30, "telegram_token": "t", "telegram_chat_id": "c"}
    )()
    mock_fetch.return_value = [
        {"productId": 1, "productName": "A", "productPrice": 1000, "discountRate": 50, "productUrl": "u1"},
        {"productId": 2, "productName": "B", "productPrice": 2000, "discountRate": 10, "productUrl": "u2"},
        {"productId": 3, "productName": "C", "productPrice": 3000, "discountRate": 60, "productUrl": "u3"},
    ]
    mock_load_sent.return_value = {3: None}  # 3번은 이미 발송됨

    sent_count = main.run()

    assert sent_count == 1  # 1번만 신규 + 고할인 (2번은 할인율 미달, 3번은 중복)
    mock_send.assert_called_once()
    call_args = mock_send.call_args[0]  # (token, chat_id, message)
    assert call_args[0] == "t"
    assert call_args[1] == "c"
    assert "A" in call_args[2]  # deal 1's productName reached send, not deal 2/3

    mock_save_sent.assert_called_once()
    saved_ids = mock_save_sent.call_args[0][1]
    assert 1 in saved_ids
