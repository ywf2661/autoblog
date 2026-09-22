# 쿠팡파트너스 특가봇

쿠팡파트너스 골드박스 특가 상품을 3시간마다 확인해 할인율 30% 이상 신규 상품을 텔레그램으로 전송합니다.

## 로컬 실행

1. `pip install -r requirements.txt`
2. `.env.example`을 `.env`로 복사 후 값 채우기
3. `python main.py`

## 환경변수

| 이름 | 설명 |
|---|---|
| COUPANG_ACCESS_KEY | 쿠팡파트너스 오픈API access key |
| COUPANG_SECRET_KEY | 쿠팡파트너스 오픈API secret key |
| TELEGRAM_BOT_TOKEN | @BotFather로 발급받은 봇 토큰 |
| TELEGRAM_CHAT_ID | 메시지를 받을 채팅방 id |
| MIN_DISCOUNT_RATE | 이 값(%) 이상 할인 상품만 전송 (기본 30) |

## 배포

GitHub Actions가 3시간마다 자동 실행 (`.github/workflows/dealbot.yml`). 저장소 Secrets에 위 4개 값 등록 필요.

## 테스트

`pytest -v`
