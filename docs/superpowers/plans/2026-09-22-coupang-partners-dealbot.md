# 쿠팡파트너스 특가봇 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 쿠팡파트너스 골드박스 특가 상품을 주기적으로 조회해, 할인율 기준을 넘는 신규 상품만 텔레그램 채널/봇으로 자동 발송한다.

**Architecture:** Python 단일 스크립트 묶음(main.py + 4개 모듈). 쿠팡파트너스 공식 오픈API(골드박스)로 특가 상품을 가져와(스크래핑 없음, ToS 준수) 할인율 필터링 → JSON 파일로 중복전송 방지 → 텔레그램 Bot API로 발송. 서버 없이 GitHub Actions의 cron 스케줄로 3시간마다 실행.

**Tech Stack:** Python 3.11+, requests, python-dotenv, pytest(dev), GitHub Actions(스케줄러/배포), Telegram Bot API, 쿠팡파트너스 오픈API(골드박스)

**Spec:** 별도 스펙 문서 없음 — 이 문서의 Goal/Architecture 절이 스펙을 겸함 (단일 기능 소규모 프로젝트)

## Global Constraints

- Python 3.11+, 표준 라이브러리 우선. 외부 의존성은 `requests`, `python-dotenv`, `pytest`만 사용 (그 외 추가 금지)
- 크롤링/스크래핑 금지 — 쿠팡파트너스 공식 오픈API만 사용 (ToS 준수, 계정정지 리스크 회피)
- API 키/토큰은 환경변수로만 관리, `.env`는 `.gitignore`에 포함하고 저장소에 절대 커밋하지 않음
- 서버 비용 0원 목표 — 배포는 GitHub Actions cron으로만 (VPS/PaaS 사용 안 함)
- 모든 순수 로직 함수(필터링, 중복체크, 메시지 포맷)는 pytest로 테스트. 외부 API 호출은 `unittest.mock`으로 모킹 (추가 mocking 라이브러리 설치 금지)

---

## File Structure

```
money-project/
├── config.py           # 환경변수 로딩 (Settings)
├── signing.py          # 쿠팡파트너스 API HMAC 서명
├── coupang_api.py       # 골드박스 API 호출
├── filters.py           # 할인율 필터링
├── dedup.py              # 중복전송 방지 (JSON 파일 기반)
├── telegram.py           # 메시지 포맷 + 텔레그램 전송
├── main.py                # 오케스트레이션 (run())
├── requirements.txt
├── .env.example
├── .gitignore
├── sent_ids.json          # 런타임에 생성됨 (git에 커밋되어 이력 유지)
├── tests/
│   ├── test_config.py
│   ├── test_signing.py
│   ├── test_coupang_api.py
│   ├── test_filters.py
│   ├── test_dedup.py
│   ├── test_telegram.py
│   └── test_main.py
├── .github/workflows/dealbot.yml
└── README.md
```

---

### Task 1: 사전 준비 (계정/키 발급)

코드 작업 전 필요한 외부 계정 승인 절차. 승인에 수일 걸릴 수 있으므로 가장 먼저 진행.

- [ ] **Step 1: 쿠팡파트너스 가입 및 오픈API 키 발급**

https://partners.coupang.com 가입 → 승인 후 https://developers.coupangcorp.com 에서 ACCESS KEY / SECRET KEY 발급. 발급 즉시 메모장 등 안전한 곳에 보관 (재확인 불가한 경우 많음).

- [ ] **Step 2: 텔레그램 봇 생성**

텔레그램에서 `@BotFather` 검색 → `/newbot` → 봇 이름 설정 → 발급된 `BOT_TOKEN` 저장.

- [ ] **Step 3: 발송받을 chat_id 확인**

봇과 대화 시작(또는 채널에 봇 추가 후 관리자 지정) → 아무 메시지나 전송 → 브라우저에서 `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` 접속 → 응답 JSON에서 `chat.id` 값 확인 및 저장.

- [ ] **Step 4: 로컬 `.env` 파일 생성**

Task 2에서 만들 `.env.example`을 복사해 `.env`로 저장하고 위에서 얻은 4개 값을 채워 넣는다 (Task 2 완료 후 진행).

---

### Task 2: 프로젝트 스캐폴딩 + 설정 로더

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Settings` dataclass (`access_key`, `secret_key`, `telegram_token`, `telegram_chat_id`, `min_discount_rate: int`), `load_settings() -> Settings`

- [ ] **Step 1: 기본 파일 작성**

`requirements.txt`:
```
requests
python-dotenv
pytest
```

`.env.example`:
```
COUPANG_ACCESS_KEY=
COUPANG_SECRET_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
MIN_DISCOUNT_RATE=30
```

`.gitignore`:
```
.env
__pycache__/
*.pyc
sent_ids.json.bak
```

- [ ] **Step 2: 의존성 설치**

Run: `pip install -r requirements.txt`

- [ ] **Step 3: 실패하는 테스트 작성**

`tests/test_config.py`:
```python
import pytest

from config import load_settings


def test_load_settings_raises_when_keys_missing(monkeypatch):
    monkeypatch.delenv("COUPANG_ACCESS_KEY", raising=False)
    monkeypatch.delenv("COUPANG_SECRET_KEY", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(RuntimeError, match="필수 환경변수 누락"):
        load_settings()


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("COUPANG_ACCESS_KEY", "ak")
    monkeypatch.setenv("COUPANG_SECRET_KEY", "sk")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tt")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "cid")
    monkeypatch.delenv("MIN_DISCOUNT_RATE", raising=False)

    settings = load_settings()

    assert settings.access_key == "ak"
    assert settings.min_discount_rate == 30
```

- [ ] **Step 4: 테스트 실행 → 실패 확인**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with "No module named 'config'"

- [ ] **Step 5: `config.py` 구현**

```python
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    access_key: str
    secret_key: str
    telegram_token: str
    telegram_chat_id: str
    min_discount_rate: int = 30


def load_settings() -> Settings:
    load_dotenv()
    required = [
        "COUPANG_ACCESS_KEY",
        "COUPANG_SECRET_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"필수 환경변수 누락: {', '.join(missing)}")

    return Settings(
        access_key=os.environ["COUPANG_ACCESS_KEY"],
        secret_key=os.environ["COUPANG_SECRET_KEY"],
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=os.environ["TELEGRAM_CHAT_ID"],
        min_discount_rate=int(os.getenv("MIN_DISCOUNT_RATE", "30")),
    )
```

- [ ] **Step 6: 테스트 실행 → 통과 확인**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore config.py tests/test_config.py
git commit -m "feat: add config loader with env validation"
```

---

### Task 3: 쿠팡파트너스 API 서명 (HMAC)

**Files:**
- Create: `signing.py`
- Test: `tests/test_signing.py`

**Interfaces:**
- Consumes: 없음 (순수 함수)
- Produces: `generate_hmac_signature(secret_key: str, method: str, path: str, query: str = "") -> tuple[str, str]` (signed_date, signature), `build_auth_header(access_key: str, secret_key: str, method: str, path: str, query: str = "") -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_signing.py`:
```python
from signing import generate_hmac_signature, build_auth_header


def test_generate_hmac_signature_changes_with_secret():
    _, sig_a = generate_hmac_signature("secret-a", "GET", "/v2/path", "")
    _, sig_b = generate_hmac_signature("secret-b", "GET", "/v2/path", "")
    assert sig_a != sig_b


def test_signature_is_64_char_hex():
    _, sig = generate_hmac_signature("secret", "GET", "/v2/path", "")
    assert len(sig) == 64
    int(sig, 16)  # 16진수가 아니면 ValueError


def test_build_auth_header_format():
    header = build_auth_header("AK123", "secret", "GET", "/v2/path", "")
    assert header.startswith("CEA algorithm=HmacSHA256, access-key=AK123, signed-date=")
    assert "signature=" in header
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `pytest tests/test_signing.py -v`
Expected: FAIL with "No module named 'signing'"

- [ ] **Step 3: `signing.py` 구현**

```python
import hashlib
import hmac
import time


def generate_hmac_signature(
    secret_key: str, method: str, path: str, query: str = ""
) -> tuple[str, str]:
    """쿠팡파트너스 API 서명 생성. (signed_date, signature) 튜플 반환."""
    signed_date = (
        time.strftime("%y%m%d", time.gmtime())
        + "T"
        + time.strftime("%H%M%S", time.gmtime())
        + "Z"
    )
    message = signed_date + method + path + query
    signature = hmac.new(
        secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return signed_date, signature


def build_auth_header(
    access_key: str, secret_key: str, method: str, path: str, query: str = ""
) -> str:
    signed_date, signature = generate_hmac_signature(secret_key, method, path, query)
    return (
        f"CEA algorithm=HmacSHA256, access-key={access_key}, "
        f"signed-date={signed_date}, signature={signature}"
    )
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `pytest tests/test_signing.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add signing.py tests/test_signing.py
git commit -m "feat: add coupang partners hmac signing"
```

---

### Task 4: 골드박스 특가 상품 조회

**Files:**
- Create: `coupang_api.py`
- Test: `tests/test_coupang_api.py`

**Interfaces:**
- Consumes: `Settings` (Task 2), `build_auth_header` (Task 3)
- Produces: `fetch_goldbox_deals(settings: Settings) -> list[dict]` — 각 dict는 최소 `productId`, `productName`, `productPrice`, `productUrl`, `discountRate` 키를 가짐

⚠️ **주의:** 골드박스 API의 정확한 응답 필드명은 쿠팡파트너스 개발자센터 문서(https://developers.coupangcorp.com)에서 API 키 발급 후 반드시 1회 확인할 것. 아래 코드는 공개된 구현 예시를 기반으로 한 필드명이며 실제와 다를 경우 Task 4 재작업 필요.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_coupang_api.py`:
```python
from unittest.mock import MagicMock, patch

from config import Settings
from coupang_api import fetch_goldbox_deals


@patch("coupang_api.requests.get")
def test_fetch_goldbox_deals_returns_product_list(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "productData": [
                {
                    "productId": 1,
                    "productName": "test",
                    "productPrice": 1000,
                    "productUrl": "http://x",
                    "discountRate": 50,
                }
            ]
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    settings = Settings("ak", "sk", "tt", "cid")
    deals = fetch_goldbox_deals(settings)

    assert len(deals) == 1
    assert deals[0]["productId"] == 1


@patch("coupang_api.requests.get")
def test_fetch_goldbox_deals_raises_on_http_error(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = RuntimeError("HTTP 500")
    mock_get.return_value = mock_response

    settings = Settings("ak", "sk", "tt", "cid")

    with pytest.raises(RuntimeError):
        fetch_goldbox_deals(settings)
```

파일 상단에 `import pytest` 추가 필요.

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `pytest tests/test_coupang_api.py -v`
Expected: FAIL with "No module named 'coupang_api'"

- [ ] **Step 3: `coupang_api.py` 구현**

```python
import requests

from config import Settings
from signing import build_auth_header

BASE_URL = "https://api-gateway.coupang.com"
GOLDBOX_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/goldbox"


def fetch_goldbox_deals(settings: Settings) -> list[dict]:
    """쿠팡파트너스 골드박스 특가 상품 목록 조회."""
    headers = {
        "Authorization": build_auth_header(
            settings.access_key, settings.secret_key, "GET", GOLDBOX_PATH
        ),
        "Content-Type": "application/json;charset=UTF-8",
    }
    response = requests.get(BASE_URL + GOLDBOX_PATH, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json().get("data", {}).get("productData", [])
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `pytest tests/test_coupang_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add coupang_api.py tests/test_coupang_api.py
git commit -m "feat: fetch goldbox deals from coupang partners api"
```

---

### Task 5: 할인율 필터링

**Files:**
- Create: `filters.py`
- Test: `tests/test_filters.py`

**Interfaces:**
- Consumes: `fetch_goldbox_deals`의 반환값과 동일한 형태의 `list[dict]`
- Produces: `filter_deals(deals: list[dict], min_discount_rate: int) -> list[dict]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_filters.py`:
```python
from filters import filter_deals


def test_filter_deals_keeps_only_high_discount():
    deals = [
        {"productId": 1, "discountRate": 50},
        {"productId": 2, "discountRate": 10},
        {"productId": 3, "discountRate": 30},
    ]

    result = filter_deals(deals, min_discount_rate=30)

    assert [d["productId"] for d in result] == [1, 3]


def test_filter_deals_treats_missing_rate_as_zero():
    deals = [{"productId": 1}]

    result = filter_deals(deals, min_discount_rate=1)

    assert result == []
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `pytest tests/test_filters.py -v`
Expected: FAIL with "No module named 'filters'"

- [ ] **Step 3: `filters.py` 구현**

```python
def filter_deals(deals: list[dict], min_discount_rate: int) -> list[dict]:
    """할인율이 min_discount_rate 이상인 상품만 남긴다."""
    return [d for d in deals if d.get("discountRate", 0) >= min_discount_rate]
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `pytest tests/test_filters.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add filters.py tests/test_filters.py
git commit -m "feat: add discount rate filter"
```

---

### Task 6: 중복전송 방지

**Files:**
- Create: `dedup.py`
- Test: `tests/test_dedup.py`

**Interfaces:**
- Consumes: `filter_deals`의 반환값과 동일한 형태의 `list[dict]` (각 dict는 `productId` 포함)
- Produces: `load_sent_ids(path: str) -> set[int]`, `save_sent_ids(path: str, sent_ids: set[int]) -> None`, `filter_unsent(deals: list[dict], sent_ids: set[int]) -> list[dict]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_dedup.py`:
```python
import os
import tempfile

from dedup import load_sent_ids, save_sent_ids, filter_unsent


def test_load_sent_ids_returns_empty_set_when_file_missing():
    assert load_sent_ids("/tmp/does-not-exist-xyz.json") == set()


def test_save_and_load_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sent.json")
        save_sent_ids(path, {1, 2, 3})

        result = load_sent_ids(path)

        assert result == {1, 2, 3}


def test_filter_unsent_excludes_already_sent():
    deals = [{"productId": 1}, {"productId": 2}]

    result = filter_unsent(deals, sent_ids={1})

    assert result == [{"productId": 2}]
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `pytest tests/test_dedup.py -v`
Expected: FAIL with "No module named 'dedup'"

- [ ] **Step 3: `dedup.py` 구현**

```python
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
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `pytest tests/test_dedup.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add dedup.py tests/test_dedup.py
git commit -m "feat: add json-based dedup store for sent products"
```

---

### Task 7: 텔레그램 메시지 포맷 + 전송

**Files:**
- Create: `telegram.py`
- Test: `tests/test_telegram.py`

**Interfaces:**
- Consumes: 단일 deal `dict` (Task 4 반환 요소와 동일한 형태)
- Produces: `format_deal_message(deal: dict) -> str`, `send_telegram_message(token: str, chat_id: str, text: str) -> None`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_telegram.py`:
```python
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
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `pytest tests/test_telegram.py -v`
Expected: FAIL with "No module named 'telegram'"

- [ ] **Step 3: `telegram.py` 구현**

```python
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
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `pytest tests/test_telegram.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add telegram.py tests/test_telegram.py
git commit -m "feat: add telegram message formatting and sending"
```

---

### Task 8: 메인 오케스트레이션

**Files:**
- Create: `main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `load_settings` (Task 2), `fetch_goldbox_deals` (Task 4), `filter_deals` (Task 5), `load_sent_ids`/`save_sent_ids`/`filter_unsent` (Task 6), `format_deal_message`/`send_telegram_message` (Task 7)
- Produces: `run() -> int` (새로 전송한 상품 개수 반환)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_main.py`:
```python
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
    mock_load_sent.return_value = {3}  # 3번은 이미 발송됨

    sent_count = main.run()

    assert sent_count == 1  # 1번만 신규 + 고할인 (2번은 할인율 미달, 3번은 중복)
    mock_send.assert_called_once()
    mock_save_sent.assert_called_once()
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with "No module named 'main'"

- [ ] **Step 3: `main.py` 구현**

```python
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
        sent_ids.add(deal["productId"])

    save_sent_ids(SENT_IDS_PATH, sent_ids)
    return len(new_deals)


if __name__ == "__main__":
    count = run()
    print(f"전송 완료: {count}건")
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `pytest tests/test_main.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 실제 키로 1회 수동 실행 (Task 1에서 준비한 `.env` 필요)**

Run: `python main.py`
Expected: 콘솔에 "전송 완료: N건" 출력, 텔레그램으로 실제 메시지 수신 확인

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: wire up dealbot orchestration in main.run"
```

---

### Task 9: GitHub Actions 크론 배포

**Files:**
- Create: `.github/workflows/dealbot.yml`

- [ ] **Step 1: 워크플로 작성**

`.github/workflows/dealbot.yml`:
```yaml
name: coupang-dealbot

on:
  schedule:
    - cron: "0 */3 * * *"  # 3시간마다 (UTC 기준)
  workflow_dispatch: {}

permissions:
  contents: write

jobs:
  run-bot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - env:
          COUPANG_ACCESS_KEY: ${{ secrets.COUPANG_ACCESS_KEY }}
          COUPANG_SECRET_KEY: ${{ secrets.COUPANG_SECRET_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python main.py
      - name: sent_ids.json 커밋 (중복전송 이력 유지)
        run: |
          git config user.name "dealbot"
          git config user.email "dealbot@users.noreply.github.com"
          git add sent_ids.json
          git diff --staged --quiet || git commit -m "chore: update sent_ids"
          git push
```

- [ ] **Step 2: GitHub 저장소에 Secrets 등록**

저장소 Settings → Secrets and variables → Actions → New repository secret 으로 4개 등록: `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

- [ ] **Step 3: 푸시 후 수동 트리거로 검증**

```bash
git add .github/workflows/dealbot.yml
git commit -m "ci: schedule dealbot via github actions"
git push
```

GitHub 저장소 → Actions 탭 → `coupang-dealbot` → "Run workflow" 클릭
Expected: 워크플로 성공(녹색 체크), 텔레그램 메시지 수신, `sent_ids.json`이 저장소에 커밋됨

---

### Task 10: 운영 문서 (README)

**Files:**
- Create: `README.md`

- [ ] **Step 1: README 작성**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add setup and operations guide"
```

---

## Self-Review Notes

- **스펙 커버리지:** 계정 발급(T1) → 설정(T2) → 인증(T3) → 특가 조회(T4) → 필터(T5) → 중복방지(T6) → 발송(T7) → 오케스트레이션(T8) → 배포(T9) → 문서(T10). 목표(할인 특가 자동 텔레그램 발송)를 빠짐없이 커버.
- **플레이스홀더 스캔:** 전 태스크 코드/테스트 완전 작성, "TODO" 없음. 단, Task 4는 실제 API 응답 필드명을 개발자센터 문서로 최초 확인 필요함을 명시 (외부 문서 의존이라 불가피).
- **타입/시그니처 일관성:** `Settings`, `fetch_goldbox_deals`, `filter_deals`, `filter_unsent`, `format_deal_message`, `send_telegram_message`, `run()` 시그니처가 태스크 간 동일하게 사용됨을 확인.
