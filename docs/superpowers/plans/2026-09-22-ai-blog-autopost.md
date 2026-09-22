# AI 블로그 자동 포스팅 봇 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI(Claude 등) 관련 RSS 피드를 매일 1건 수집해 Claude API로 재작성하고, 쿠팡파트너스 관련상품 링크를 삽입해 Blogger에 임시저장(draft) 글로 생성한다. 공개 발행은 사람이 수동으로 한다.

**Architecture:** Python 단일 스크립트 묶음(`blogbot/` 폴더, main.py + 7개 모듈). RSS 수집 → 중복 제외 → Claude API 재작성 → 쿠팡파트너스 상품검색 API → HTML 조립 → Blogger API(OAuth refresh_token) draft 생성. 서버 없이 GitHub Actions cron으로 매일 1회 실행.

**Tech Stack:** Python 3.11+, requests, python-dotenv, feedparser, pytest(dev), GitHub Actions(스케줄러/배포), Anthropic Claude API, 쿠팡파트너스 오픈API(상품검색), Google Blogger API v3

**Spec:** `docs/superpowers/specs/2026-09-22-ai-blog-autopost-design.md`

## Global Constraints

- Python 3.11+, 표준 라이브러리 우선. 외부 의존성은 `requests`, `python-dotenv`, `feedparser`, `pytest`만 사용 (SDK류 추가 금지)
- 콘텐츠는 RSS 요약만 참고해 완전 재작성 — 원문 전문 크롤링 금지
- 자동화는 Draft(임시저장) 생성까지만. 공개 발행은 사람이 수동으로
- 하루 처리 기사 1건 (신규 기사 중 published 최신 1건만)
- API 키/토큰은 환경변수로만 관리, `.env`는 `.gitignore`에 포함, 저장소에 절대 커밋하지 않음
- 서버 비용 0원 목표 — 배포는 GitHub Actions cron으로만
- 순수 로직 함수는 pytest로 테스트, 외부 API 호출은 `unittest.mock`으로 모킹 (추가 mocking 라이브러리 설치 금지)
- dealbot(별도 계획, 루트 파일 예정)과 모듈명 충돌 방지를 위해 전부 `blogbot/` 하위 폴더에 격리

---

## File Structure

```
money-project/
├── blogbot/
│   ├── config.py
│   ├── dedup.py
│   ├── signing.py
│   ├── coupang_search.py
│   ├── rss_reader.py
│   ├── article_writer.py
│   ├── content_assembler.py
│   ├── blogger_api.py
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── feeds.txt
│   ├── posted_ids.json
│   ├── tests/
│   │   ├── test_config.py
│   │   ├── test_dedup.py
│   │   ├── test_signing.py
│   │   ├── test_coupang_search.py
│   │   ├── test_rss_reader.py
│   │   ├── test_article_writer.py
│   │   ├── test_content_assembler.py
│   │   ├── test_blogger_api.py
│   │   └── test_main.py
│   └── README.md
└── .github/workflows/blogbot.yml
```

---

### Task 1: 사전 준비 (계정/키 발급)

코드 작업 전 필요한 외부 계정/키 준비. 승인에 시간이 걸릴 수 있으므로 가장 먼저 진행.

- [ ] **Step 1: Blogger 블로그 생성**

https://www.blogger.com 에서 블로그 생성. 블로그 URL의 `blogID`는 Blogger 설정 페이지(Settings → 기본 정보)에서 확인 가능(또는 `https://www.googleapis.com/blogger/v3/blogs/byurl?url=<블로그URL>&key=<API키>` 호출로도 확인 가능).

- [ ] **Step 2: 애드센스 연결**

블로그 설정에서 애드센스 연결/승인 신청 (승인까지 수일~수주 소요 가능, 별도 진행).

- [ ] **Step 3: Google Cloud OAuth 클라이언트 발급**

https://console.cloud.google.com → 프로젝트 생성 → "API 및 서비스" → "사용자 인증 정보" → "OAuth 클라이언트 ID" 생성, 애플리케이션 유형은 **데스크톱 앱**. `client_id`/`client_secret` 저장. 같은 화면에서 "Blogger API"를 라이브러리에서 검색해 사용 설정(Enable).

- [ ] **Step 4: refresh_token 1회 발급**

로컬에 임시 스크립트를 저장하고 실행한다 (저장소에는 커밋하지 않음, 1회용).

`get_refresh_token.py` (프로젝트 밖 아무 폴더에나 임시로 저장):
```python
import sys
import urllib.parse

import requests

SCOPE = "https://www.googleapis.com/auth/blogger"
REDIRECT_URI = "http://localhost:8080"


def main():
    client_id, client_secret = sys.argv[1], sys.argv[2]

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
    print(f"브라우저에서 다음 URL을 열고 로그인/동의하세요:\n{auth_url}\n")
    print("동의 후 리디렉션되는 주소(로딩 실패 페이지)의 주소창에서 'code=' 뒤의 값을 복사하세요.")
    code = input("code 값을 붙여넣으세요: ").strip()

    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    })
    response.raise_for_status()
    print("refresh_token:", response.json()["refresh_token"])


if __name__ == "__main__":
    main()
```

Run: `pip install requests` (아직 없다면) `python get_refresh_token.py <CLIENT_ID> <CLIENT_SECRET>`
출력된 `refresh_token` 값을 안전한 곳에 저장. 실행 후 이 스크립트 파일은 삭제해도 무방.

⚠️ OAuth 동의 화면이 "테스트" 상태면 refresh_token이 7일 후 만료될 수 있음. Google Cloud Console → "OAuth 동의 화면"에서 "게시 상태"를 확인하고, 필요시 게시(외부 사용자 대상 "프로덕션"으로 전환)할 것. 개인 전용 앱이라 Google 심사 없이도 게시 가능(민감 스코프가 아닌 경우).

- [ ] **Step 5: Anthropic API 키 발급**

https://console.anthropic.com 에서 API 키 발급.

- [ ] **Step 6: 쿠팡파트너스 키 확보**

dealbot에서 이미 발급받았다면 동일 `ACCESS KEY`/`SECRET KEY` 재사용. 없다면 https://partners.coupang.com 가입 → https://developers.coupangcorp.com 에서 발급.

- [ ] **Step 7: 로컬 `.env` 파일 생성**

Task 2에서 만들 `.env.example`을 `blogbot/.env`로 복사해 위에서 얻은 값들을 채운다 (Task 2 완료 후 진행).

---

### Task 2: 프로젝트 스캐폴딩 + 설정 로더

**Files:**
- Create: `blogbot/requirements.txt`
- Create: `blogbot/.env.example`
- Create: `blogbot/config.py`
- Test: `blogbot/tests/test_config.py`

**Interfaces:**
- Produces: `Settings` dataclass (`anthropic_api_key`, `coupang_access_key`, `coupang_secret_key`, `google_client_id`, `google_client_secret`, `google_refresh_token`, `blogger_blog_id`), `load_settings() -> Settings`

- [ ] **Step 1: 기본 파일 작성**

`blogbot/requirements.txt`:
```
requests
python-dotenv
feedparser
pytest
```

`blogbot/.env.example`:
```
ANTHROPIC_API_KEY=
COUPANG_ACCESS_KEY=
COUPANG_SECRET_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
BLOGGER_BLOG_ID=
```

루트 `.gitignore`에 이미 `.env`가 포함되어 있는지 확인하고, 없다면 추가한다.

- [ ] **Step 2: 의존성 설치**

Run: `cd blogbot && pip install -r requirements.txt`

- [ ] **Step 3: 실패하는 테스트 작성**

`blogbot/tests/test_config.py`:
```python
import pytest

from config import load_settings


def test_load_settings_raises_when_keys_missing(monkeypatch):
    for key in [
        "ANTHROPIC_API_KEY",
        "COUPANG_ACCESS_KEY",
        "COUPANG_SECRET_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
        "BLOGGER_BLOG_ID",
    ]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError, match="필수 환경변수 누락"):
        load_settings()


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ak")
    monkeypatch.setenv("COUPANG_ACCESS_KEY", "cak")
    monkeypatch.setenv("COUPANG_SECRET_KEY", "csk")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "gcid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "gcs")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "grt")
    monkeypatch.setenv("BLOGGER_BLOG_ID", "blogid")

    settings = load_settings()

    assert settings.anthropic_api_key == "ak"
    assert settings.blogger_blog_id == "blogid"
```

- [ ] **Step 4: 테스트 실행 → 실패 확인**

Run: `cd blogbot && pytest tests/test_config.py -v`
Expected: FAIL with "No module named 'config'"

- [ ] **Step 5: `config.py` 구현**

`blogbot/config.py`:
```python
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    anthropic_api_key: str
    coupang_access_key: str
    coupang_secret_key: str
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    blogger_blog_id: str


def load_settings() -> Settings:
    load_dotenv()
    required = [
        "ANTHROPIC_API_KEY",
        "COUPANG_ACCESS_KEY",
        "COUPANG_SECRET_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
        "BLOGGER_BLOG_ID",
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"필수 환경변수 누락: {', '.join(missing)}")

    return Settings(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        coupang_access_key=os.environ["COUPANG_ACCESS_KEY"],
        coupang_secret_key=os.environ["COUPANG_SECRET_KEY"],
        google_client_id=os.environ["GOOGLE_CLIENT_ID"],
        google_client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        google_refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        blogger_blog_id=os.environ["BLOGGER_BLOG_ID"],
    )
```

- [ ] **Step 6: 테스트 실행 → 통과 확인**

Run: `cd blogbot && pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add blogbot/requirements.txt blogbot/.env.example blogbot/config.py blogbot/tests/test_config.py .gitignore
git commit -m "feat(blogbot): add config loader with env validation"
```

---

### Task 3: 중복 게시 방지 (dedup)

**Files:**
- Create: `blogbot/dedup.py`
- Test: `blogbot/tests/test_dedup.py`

**Interfaces:**
- Consumes: 없음 (순수 함수)
- Produces: `hash_link(link: str) -> str`, `load_posted_ids(path: str) -> set[str]`, `save_posted_ids(path: str, ids: set[str]) -> None`, `pick_next_entry(entries: list[dict], posted_ids: set[str]) -> dict | None` (entries의 각 dict는 `link`, `published` 키를 가짐. `published`는 비교 가능한 값, 예: `time.struct_time`)

- [ ] **Step 1: 실패하는 테스트 작성**

`blogbot/tests/test_dedup.py`:
```python
import time

from dedup import hash_link, load_posted_ids, save_posted_ids, pick_next_entry


def test_load_posted_ids_returns_empty_set_when_file_missing():
    assert load_posted_ids("/tmp/does-not-exist-blogbot.json") == set()


def test_save_and_load_round_trip(tmp_path):
    path = str(tmp_path / "posted.json")
    save_posted_ids(path, {"aaa", "bbb"})

    result = load_posted_ids(path)

    assert result == {"aaa", "bbb"}


def test_pick_next_entry_picks_latest_unposted():
    old = time.struct_time((2026, 9, 20, 0, 0, 0, 0, 0, 0))
    new = time.struct_time((2026, 9, 22, 0, 0, 0, 0, 0, 0))
    entries = [
        {"link": "http://a", "published": old},
        {"link": "http://b", "published": new},
    ]

    result = pick_next_entry(entries, posted_ids=set())

    assert result["link"] == "http://b"


def test_pick_next_entry_returns_none_when_all_posted():
    entry = {
        "link": "http://a",
        "published": time.struct_time((2026, 9, 20, 0, 0, 0, 0, 0, 0)),
    }

    result = pick_next_entry([entry], posted_ids={hash_link("http://a")})

    assert result is None
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd blogbot && pytest tests/test_dedup.py -v`
Expected: FAIL with "No module named 'dedup'"

- [ ] **Step 3: `dedup.py` 구현**

`blogbot/dedup.py`:
```python
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
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `cd blogbot && pytest tests/test_dedup.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add blogbot/dedup.py blogbot/tests/test_dedup.py
git commit -m "feat(blogbot): add posted-articles dedup store"
```

---

### Task 4: 쿠팡파트너스 API 서명 (HMAC)

**Files:**
- Create: `blogbot/signing.py`
- Test: `blogbot/tests/test_signing.py`

**Interfaces:**
- Consumes: 없음 (순수 함수)
- Produces: `generate_hmac_signature(secret_key: str, method: str, path: str, query: str = "") -> tuple[str, str]`, `build_auth_header(access_key: str, secret_key: str, method: str, path: str, query: str = "") -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

`blogbot/tests/test_signing.py`:
```python
from signing import generate_hmac_signature, build_auth_header


def test_generate_hmac_signature_changes_with_secret():
    _, sig_a = generate_hmac_signature("secret-a", "GET", "/v2/path", "")
    _, sig_b = generate_hmac_signature("secret-b", "GET", "/v2/path", "")
    assert sig_a != sig_b


def test_signature_is_64_char_hex():
    _, sig = generate_hmac_signature("secret", "GET", "/v2/path", "")
    assert len(sig) == 64
    int(sig, 16)


def test_build_auth_header_format():
    header = build_auth_header("AK123", "secret", "GET", "/v2/path", "")
    assert header.startswith("CEA algorithm=HmacSHA256, access-key=AK123, signed-date=")
    assert "signature=" in header
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd blogbot && pytest tests/test_signing.py -v`
Expected: FAIL with "No module named 'signing'"

- [ ] **Step 3: `signing.py` 구현**

`blogbot/signing.py`:
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

Run: `cd blogbot && pytest tests/test_signing.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add blogbot/signing.py blogbot/tests/test_signing.py
git commit -m "feat(blogbot): add coupang partners hmac signing"
```

---

### Task 5: 쿠팡파트너스 상품 검색

**Files:**
- Create: `blogbot/coupang_search.py`
- Test: `blogbot/tests/test_coupang_search.py`

**Interfaces:**
- Consumes: `Settings` (Task 2), `build_auth_header` (Task 4)
- Produces: `search_products(settings: Settings, keyword: str, limit: int = 3) -> list[dict]` — 각 dict는 `productName`, `productUrl`, `productImage`, `productPrice` 키를 가짐. 실패 시 빈 리스트

- [ ] **Step 1: 실패하는 테스트 작성**

`blogbot/tests/test_coupang_search.py`:
```python
from unittest.mock import MagicMock, patch

import requests

from config import Settings
from coupang_search import search_products


def _settings():
    return Settings("ak", "cak", "csk", "gcid", "gcs", "grt", "blogid")


@patch("coupang_search.requests.get")
def test_search_products_returns_product_list(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "data": {
            "productData": [
                {
                    "productName": "노트북",
                    "productUrl": "http://x",
                    "productImage": "http://img",
                    "productPrice": 1000000,
                }
            ]
        }
    }
    mock_get.return_value = mock_response

    result = search_products(_settings(), "노트북")

    assert len(result) == 1
    assert result[0]["productName"] == "노트북"


@patch("coupang_search.requests.get")
def test_search_products_returns_empty_list_on_request_error(mock_get):
    mock_get.side_effect = requests.RequestException("boom")

    result = search_products(_settings(), "노트북")

    assert result == []
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd blogbot && pytest tests/test_coupang_search.py -v`
Expected: FAIL with "No module named 'coupang_search'"

- [ ] **Step 3: `coupang_search.py` 구현**

`blogbot/coupang_search.py`:
```python
import requests

from config import Settings
from signing import build_auth_header

BASE_URL = "https://api-gateway.coupang.com"
SEARCH_PATH = "/v2/providers/affiliate_open_api/apis/openapi/products/search"


def search_products(settings: Settings, keyword: str, limit: int = 3) -> list[dict]:
    """키워드로 쿠팡파트너스 상품을 검색한다. 실패하거나 결과가 없으면 빈 리스트를 반환."""
    query = f"keyword={keyword}&limit={limit}"
    headers = {
        "Authorization": build_auth_header(
            settings.coupang_access_key,
            settings.coupang_secret_key,
            "GET",
            SEARCH_PATH,
            query,
        ),
        "Content-Type": "application/json;charset=UTF-8",
    }
    try:
        response = requests.get(
            f"{BASE_URL}{SEARCH_PATH}?{query}", headers=headers, timeout=10
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    products = response.json().get("data", {}).get("productData", [])
    return [
        {
            "productName": p.get("productName", ""),
            "productUrl": p.get("productUrl", ""),
            "productImage": p.get("productImage", ""),
            "productPrice": p.get("productPrice", 0),
        }
        for p in products[:limit]
    ]
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `cd blogbot && pytest tests/test_coupang_search.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add blogbot/coupang_search.py blogbot/tests/test_coupang_search.py
git commit -m "feat(blogbot): search coupang partners products by keyword"
```

---

### Task 6: RSS 피드 수집

**Files:**
- Create: `blogbot/rss_reader.py`
- Test: `blogbot/tests/test_rss_reader.py`

**Interfaces:**
- Consumes: 없음
- Produces: `fetch_feed_entries(feed_urls: list[str]) -> list[dict]` — 각 dict는 `title`, `summary`, `link`, `published`(`time.struct_time`) 키를 가짐

- [ ] **Step 1: 실패하는 테스트 작성**

`blogbot/tests/test_rss_reader.py`:
```python
import time
from unittest.mock import MagicMock, patch

from rss_reader import fetch_feed_entries


@patch("rss_reader.feedparser.parse")
def test_fetch_feed_entries_returns_entries_with_published(mock_parse):
    mock_parsed = MagicMock()
    mock_parsed.bozo = False
    mock_parsed.entries = [
        {
            "title": "제목",
            "summary": "요약",
            "link": "http://x",
            "published_parsed": time.struct_time((2026, 9, 22, 0, 0, 0, 0, 0, 0)),
        }
    ]
    mock_parse.return_value = mock_parsed

    entries = fetch_feed_entries(["http://feed"])

    assert len(entries) == 1
    assert entries[0]["title"] == "제목"
    assert entries[0]["link"] == "http://x"


@patch("rss_reader.feedparser.parse")
def test_fetch_feed_entries_skips_entry_without_published(mock_parse):
    mock_parsed = MagicMock()
    mock_parsed.bozo = False
    mock_parsed.entries = [{"title": "t", "summary": "s", "link": "l"}]
    mock_parse.return_value = mock_parsed

    entries = fetch_feed_entries(["http://feed"])

    assert entries == []


@patch("rss_reader.feedparser.parse")
def test_fetch_feed_entries_skips_broken_feed(mock_parse):
    mock_parsed = MagicMock()
    mock_parsed.bozo = True
    mock_parsed.entries = []
    mock_parse.return_value = mock_parsed

    entries = fetch_feed_entries(["http://broken-feed"])

    assert entries == []
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd blogbot && pytest tests/test_rss_reader.py -v`
Expected: FAIL with "No module named 'rss_reader'"

- [ ] **Step 3: `rss_reader.py` 구현**

`blogbot/rss_reader.py`:
```python
import feedparser


def fetch_feed_entries(feed_urls: list[str]) -> list[dict]:
    """RSS 피드 목록에서 항목을 수집한다. 파싱 실패한 피드는 건너뛴다."""
    entries = []
    for url in feed_urls:
        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            continue
        for entry in parsed.entries:
            published = entry.get("published_parsed")
            if published is None:
                continue
            entries.append(
                {
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                    "published": published,
                }
            )
    return entries
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `cd blogbot && pytest tests/test_rss_reader.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add blogbot/rss_reader.py blogbot/tests/test_rss_reader.py
git commit -m "feat(blogbot): fetch and parse rss feed entries"
```

---

### Task 7: Claude API로 글 재작성

**Files:**
- Create: `blogbot/article_writer.py`
- Test: `blogbot/tests/test_article_writer.py`

**Interfaces:**
- Consumes: `Settings` (Task 2), 단일 entry `dict` (Task 6 반환 요소와 동일한 형태)
- Produces: `write_article(settings: Settings, entry: dict) -> dict` — 반환값 `{title: str, body_html: str, keywords: list[str]}`. JSON 파싱 실패나 필수 필드 누락 시 `ValueError`

- [ ] **Step 1: 실패하는 테스트 작성**

`blogbot/tests/test_article_writer.py`:
```python
from unittest.mock import MagicMock, patch

import pytest

from config import Settings
from article_writer import write_article


def _settings():
    return Settings("ak", "cak", "csk", "gcid", "gcs", "grt", "blogid")


@patch("article_writer.requests.post")
def test_write_article_parses_json_response(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "content": [
            {
                "text": '{"title": "제목", "body_html": "<p>본문</p>", "keywords": ["노트북"]}'
            }
        ]
    }
    mock_post.return_value = mock_response

    result = write_article(
        _settings(), {"title": "t", "summary": "s", "link": "http://x"}
    )

    assert result["title"] == "제목"
    assert result["keywords"] == ["노트북"]


@patch("article_writer.requests.post")
def test_write_article_raises_on_invalid_json(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"content": [{"text": "이건 JSON이 아님"}]}
    mock_post.return_value = mock_response

    with pytest.raises(ValueError):
        write_article(_settings(), {"title": "t", "summary": "s", "link": "http://x"})


@patch("article_writer.requests.post")
def test_write_article_defaults_keywords_when_missing(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "content": [{"text": '{"title": "제목", "body_html": "<p>본문</p>"}'}]
    }
    mock_post.return_value = mock_response

    result = write_article(
        _settings(), {"title": "t", "summary": "s", "link": "http://x"}
    )

    assert result["keywords"] == []
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd blogbot && pytest tests/test_article_writer.py -v`
Expected: FAIL with "No module named 'article_writer'"

- [ ] **Step 3: `article_writer.py` 구현**

`blogbot/article_writer.py`:
```python
import json

import requests

from config import Settings

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"

PROMPT_TEMPLATE = """다음은 한 AI 관련 뉴스 기사의 제목과 요약이다.

제목: {title}
요약: {summary}
원문 링크: {link}

이 정보를 참고해 한국어 블로그 글을 새로 작성하라. 원문 문장을 그대로 베끼지 말고, 구성과 표현을 완전히 새로 만들어라.
글 마지막에는 "출처: {link}" 문구를 포함하라.
블로그 글과 어울리는, 쿠팡에서 검색할 수 있는 실존 상품 카테고리 키워드를 1~2개 뽑아라 (예: "노트북", "블루투스 이어폰").

다음 JSON 형식으로만 응답하라. 다른 텍스트는 포함하지 마라:
{{"title": "블로그 글 제목", "body_html": "<p>...</p>", "keywords": ["키워드1"]}}
"""


def write_article(settings: Settings, entry: dict) -> dict:
    """RSS 항목을 참고해 Claude로 블로그 글을 재작성한다."""
    prompt = PROMPT_TEMPLATE.format(
        title=entry["title"], summary=entry["summary"], link=entry["link"]
    )
    response = requests.post(
        API_URL,
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    text = response.json()["content"][0]["text"]
    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude 응답이 JSON이 아님: {text!r}") from e

    if "title" not in result or "body_html" not in result:
        raise ValueError(f"Claude 응답에 필수 필드 누락: {result!r}")
    result.setdefault("keywords", [])
    return result
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `cd blogbot && pytest tests/test_article_writer.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add blogbot/article_writer.py blogbot/tests/test_article_writer.py
git commit -m "feat(blogbot): rewrite articles via claude api"
```

---

### Task 8: 본문 + 관련 상품 HTML 조립

**Files:**
- Create: `blogbot/content_assembler.py`
- Test: `blogbot/tests/test_content_assembler.py`

**Interfaces:**
- Consumes: `body_html: str` (Task 7 반환값의 일부), `products: list[dict]` (Task 5 반환값과 동일한 형태)
- Produces: `assemble_post_html(body_html: str, products: list[dict]) -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

`blogbot/tests/test_content_assembler.py`:
```python
from content_assembler import assemble_post_html


def test_assemble_post_html_appends_products_section():
    html = assemble_post_html(
        "<p>본문</p>",
        [
            {
                "productName": "노트북",
                "productUrl": "http://x",
                "productImage": "",
                "productPrice": 1000000,
            }
        ],
    )

    assert "<p>본문</p>" in html
    assert "노트북" in html
    assert "1,000,000원" in html


def test_assemble_post_html_skips_section_when_no_products():
    html = assemble_post_html("<p>본문</p>", [])

    assert html == "<p>본문</p>"
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd blogbot && pytest tests/test_content_assembler.py -v`
Expected: FAIL with "No module named 'content_assembler'"

- [ ] **Step 3: `content_assembler.py` 구현**

`blogbot/content_assembler.py`:
```python
def assemble_post_html(body_html: str, products: list[dict]) -> str:
    """본문 HTML에 관련 상품 섹션을 덧붙인다. 상품이 없으면 본문만 반환."""
    if not products:
        return body_html

    items = "".join(
        f'<li><a href="{p["productUrl"]}">{p["productName"]}</a> - {p["productPrice"]:,}원</li>'
        for p in products
    )
    products_section = f"<h3>관련 상품</h3><ul>{items}</ul>"
    return f"{body_html}\n{products_section}"
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `cd blogbot && pytest tests/test_content_assembler.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add blogbot/content_assembler.py blogbot/tests/test_content_assembler.py
git commit -m "feat(blogbot): assemble post html with related products section"
```

---

### Task 9: Blogger API (OAuth 갱신 + draft 생성)

**Files:**
- Create: `blogbot/blogger_api.py`
- Test: `blogbot/tests/test_blogger_api.py`

**Interfaces:**
- Consumes: `Settings` (Task 2)
- Produces: `refresh_access_token(settings: Settings) -> str`, `create_draft_post(settings: Settings, access_token: str, title: str, html: str) -> str` (draft 편집 URL 반환)

- [ ] **Step 1: 실패하는 테스트 작성**

`blogbot/tests/test_blogger_api.py`:
```python
from unittest.mock import MagicMock, patch

from config import Settings
from blogger_api import refresh_access_token, create_draft_post


def _settings():
    return Settings("ak", "cak", "csk", "gcid", "gcs", "grt", "12345")


@patch("blogger_api.requests.post")
def test_refresh_access_token_returns_token(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"access_token": "new-token"}
    mock_post.return_value = mock_response

    token = refresh_access_token(_settings())

    assert token == "new-token"


@patch("blogger_api.requests.post")
def test_create_draft_post_returns_edit_url(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"id": "999"}
    mock_post.return_value = mock_response

    url = create_draft_post(_settings(), "token", "제목", "<p>본문</p>")

    assert url == "https://www.blogger.com/blog/post/edit/12345/999"
    args, kwargs = mock_post.call_args
    assert kwargs["json"] == {"title": "제목", "content": "<p>본문</p>"}
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd blogbot && pytest tests/test_blogger_api.py -v`
Expected: FAIL with "No module named 'blogger_api'"

- [ ] **Step 3: `blogger_api.py` 구현**

`blogbot/blogger_api.py`:
```python
import requests

from config import Settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
POSTS_URL = "https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"


def refresh_access_token(settings: Settings) -> str:
    """refresh_token으로 새 access_token을 발급받는다."""
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": settings.google_refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_draft_post(
    settings: Settings, access_token: str, title: str, html: str
) -> str:
    """Blogger에 임시저장(draft) 글을 생성하고 편집 URL을 반환한다."""
    url = POSTS_URL.format(blog_id=settings.blogger_blog_id) + "?isDraft=true"
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": title, "content": html},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return f"https://www.blogger.com/blog/post/edit/{settings.blogger_blog_id}/{data['id']}"
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `cd blogbot && pytest tests/test_blogger_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add blogbot/blogger_api.py blogbot/tests/test_blogger_api.py
git commit -m "feat(blogbot): create blogger drafts via oauth refresh token"
```

---

### Task 10: 메인 오케스트레이션

**Files:**
- Create: `blogbot/main.py`
- Create: `blogbot/feeds.txt`
- Test: `blogbot/tests/test_main.py`

**Interfaces:**
- Consumes: `load_settings` (Task 2), `hash_link`/`load_posted_ids`/`save_posted_ids`/`pick_next_entry` (Task 3), `search_products` (Task 5), `fetch_feed_entries` (Task 6), `write_article` (Task 7), `assemble_post_html` (Task 8), `refresh_access_token`/`create_draft_post` (Task 9)
- Produces: `run() -> str | None` (생성한 draft의 편집 URL, 새 기사가 없으면 `None`)

- [ ] **Step 1: `feeds.txt` 초기 목록 작성**

`blogbot/feeds.txt` (AI 관련 RSS. 실제 URL 유효성은 Task 1 준비 단계에서 확인/교체):
```
https://www.aitimes.com/rss/allArticle.xml
https://techcrunch.com/category/artificial-intelligence/feed/
https://www.anthropic.com/rss.xml
```

- [ ] **Step 2: 실패하는 테스트 작성**

`blogbot/tests/test_main.py`:
```python
from unittest.mock import mock_open, patch

import main


@patch("main.save_posted_ids")
@patch("main.create_draft_post")
@patch("main.refresh_access_token")
@patch("main.search_products")
@patch("main.write_article")
@patch("main.load_posted_ids")
@patch("main.fetch_feed_entries")
@patch("main.load_settings")
@patch("builtins.open", new_callable=mock_open, read_data="http://feed1\nhttp://feed2\n")
def test_run_creates_draft_for_next_entry(
    mock_file,
    mock_load_settings,
    mock_fetch,
    mock_load_posted,
    mock_write_article,
    mock_search,
    mock_refresh,
    mock_create_draft,
    mock_save_posted,
):
    mock_load_settings.return_value = object()
    mock_fetch.return_value = [
        {"title": "t", "summary": "s", "link": "http://x", "published": (2026, 9, 22)}
    ]
    mock_load_posted.return_value = set()
    mock_write_article.return_value = {
        "title": "제목",
        "body_html": "<p>본문</p>",
        "keywords": ["노트북"],
    }
    mock_search.return_value = []
    mock_refresh.return_value = "token"
    mock_create_draft.return_value = "http://blogger-edit-url"

    result = main.run()

    assert result == "http://blogger-edit-url"
    mock_save_posted.assert_called_once()
    mock_search.assert_called_once_with(mock_load_settings.return_value, "노트북")


@patch("main.load_posted_ids")
@patch("main.fetch_feed_entries")
@patch("main.load_settings")
@patch("builtins.open", new_callable=mock_open, read_data="http://feed1\n")
def test_run_returns_none_when_no_new_entry(
    mock_file, mock_load_settings, mock_fetch, mock_load_posted
):
    mock_load_settings.return_value = object()
    mock_fetch.return_value = []
    mock_load_posted.return_value = set()

    result = main.run()

    assert result is None
```

- [ ] **Step 3: 테스트 실행 → 실패 확인**

Run: `cd blogbot && pytest tests/test_main.py -v`
Expected: FAIL with "No module named 'main'"

- [ ] **Step 4: `main.py` 구현**

`blogbot/main.py`:
```python
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

    posted_ids = load_posted_ids(POSTED_IDS_PATH)
    entry = pick_next_entry(entries, posted_ids)
    if entry is None:
        return None

    article = write_article(settings, entry)

    keywords = article.get("keywords", [])
    products = search_products(settings, keywords[0]) if keywords else []

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
```

- [ ] **Step 5: 테스트 실행 → 통과 확인**

Run: `cd blogbot && pytest tests/test_main.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: 실제 키로 1회 수동 실행 (Task 1의 `.env` 필요)**

Run: `cd blogbot && python main.py`
Expected: 콘솔에 "초안 생성 완료: <URL>" 또는 "새로 게시할 기사가 없습니다." 출력. Blogger 대시보드에서 draft 확인.

- [ ] **Step 7: Commit**

```bash
git add blogbot/main.py blogbot/feeds.txt blogbot/tests/test_main.py
git commit -m "feat(blogbot): wire up blogbot orchestration in main.run"
```

---

### Task 11: GitHub Actions 크론 배포

**Files:**
- Create: `.github/workflows/blogbot.yml`

- [ ] **Step 1: 워크플로 작성**

`.github/workflows/blogbot.yml`:
```yaml
name: ai-blogbot

on:
  schedule:
    - cron: "0 0 * * *"  # 매일 UTC 00:00 (KST 09:00)
  workflow_dispatch: {}

permissions:
  contents: write

jobs:
  run-bot:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: blogbot
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          COUPANG_ACCESS_KEY: ${{ secrets.COUPANG_ACCESS_KEY }}
          COUPANG_SECRET_KEY: ${{ secrets.COUPANG_SECRET_KEY }}
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
          GOOGLE_REFRESH_TOKEN: ${{ secrets.GOOGLE_REFRESH_TOKEN }}
          BLOGGER_BLOG_ID: ${{ secrets.BLOGGER_BLOG_ID }}
        run: python main.py
      - name: posted_ids.json 커밋 (중복게시 이력 유지)
        run: |
          git config user.name "ai-blogbot"
          git config user.email "ai-blogbot@users.noreply.github.com"
          git add posted_ids.json
          git diff --staged --quiet || git commit -m "chore: update posted_ids"
          git push
```

- [ ] **Step 2: GitHub 저장소에 Secrets 등록**

저장소 Settings → Secrets and variables → Actions → New repository secret 으로 7개 등록: `ANTHROPIC_API_KEY`, `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `BLOGGER_BLOG_ID`

- [ ] **Step 3: 푸시 후 수동 트리거로 검증**

```bash
git add .github/workflows/blogbot.yml
git commit -m "ci: schedule blogbot via github actions"
git push
```

GitHub 저장소 → Actions 탭 → `ai-blogbot` → "Run workflow" 클릭
Expected: 워크플로 성공(녹색 체크), Blogger에 draft 생성, `posted_ids.json`이 저장소에 커밋됨

---

### Task 12: 운영 문서 (README)

**Files:**
- Create: `blogbot/README.md`

- [ ] **Step 1: README 작성**

`blogbot/README.md`:
```markdown
# AI 블로그 자동 포스팅 봇

AI(Claude 등) 관련 RSS 피드를 매일 1건 확인해 Claude로 재작성하고, 쿠팡파트너스 관련상품 링크를 붙여 Blogger에 임시저장(draft) 글을 생성합니다. 공개 발행은 Blogger 대시보드에서 사람이 직접 합니다.

## 로컬 실행

1. `cd blogbot && pip install -r requirements.txt`
2. `.env.example`을 `.env`로 복사 후 값 채우기 (계정/키 준비는 상위 plan의 Task 1 참고)
3. `feeds.txt`에 사용할 RSS 주소 확인/수정
4. `python main.py`

## 환경변수

| 이름 | 설명 |
|---|---|
| ANTHROPIC_API_KEY | Anthropic API 키 |
| COUPANG_ACCESS_KEY | 쿠팡파트너스 오픈API access key |
| COUPANG_SECRET_KEY | 쿠팡파트너스 오픈API secret key |
| GOOGLE_CLIENT_ID | Google OAuth 클라이언트 ID (데스크톱 앱) |
| GOOGLE_CLIENT_SECRET | Google OAuth 클라이언트 secret |
| GOOGLE_REFRESH_TOKEN | 1회 OAuth 동의로 발급받은 refresh token |
| BLOGGER_BLOG_ID | 대상 Blogger 블로그 ID |

## 배포

GitHub Actions가 매일 1회 자동 실행(`.github/workflows/blogbot.yml`, UTC 00:00 = KST 09:00). 저장소 Secrets에 위 7개 값 등록 필요.

## 발행 흐름

1. `feeds.txt`의 RSS에서 아직 다루지 않은 기사 중 가장 최근 1건 선택
2. Claude API로 완전히 새로 작성 (원문 요약만 참고, 전문 미사용)
3. 글 키워드로 쿠팡파트너스 관련상품 검색 후 본문에 섹션 추가
4. Blogger에 **draft(임시저장)**로 생성 — 공개 발행은 수동으로 Blogger 대시보드에서 진행
5. 처리한 기사는 `posted_ids.json`에 기록해 중복 방지

## 주의사항

- Google OAuth 동의 화면이 "테스트" 상태면 refresh_token이 7일 후 만료될 수 있습니다. Cloud Console에서 "게시" 상태로 전환하세요.
- 애드센스는 저품질/대량 자동생성 콘텐츠에 대한 정책이 있습니다. draft를 반드시 검토 후 발행하세요.

## 테스트

`cd blogbot && pytest -v`
```

- [ ] **Step 2: Commit**

```bash
git add blogbot/README.md
git commit -m "docs(blogbot): add setup and operations guide"
```

---

## Self-Review Notes

- **스펙 커버리지:** 사전준비(T1) → 설정(T2) → dedup(T3) → 서명(T4) → 쿠팡검색(T5) → RSS수집(T6) → Claude재작성(T7) → HTML조립(T8) → Blogger API(T9) → 오케스트레이션(T10) → 배포(T11) → 문서(T12). 스펙의 모든 컴포넌트(rss_reader, dedup, article_writer, coupang_search, content_assembler, blogger_api, main)와 사전 준비 항목(Blogger/OAuth/Anthropic/쿠팡 키, feeds.txt)을 빠짐없이 커버.
- **플레이스홀더 스캔:** 전 태스크 코드/테스트 완전 작성, "TODO" 없음. Task 1의 refresh_token 발급 스크립트는 대화형(브라우저+수동 코드 입력)이라 자동화 테스트 대상이 아님을 명시(dealbot Task 1과 동일하게 순수 설정 단계로 취급).
- **타입/시그니처 일관성:** `Settings` 필드 순서, `hash_link`/`pick_next_entry`/`search_products`/`write_article`/`assemble_post_html`/`refresh_access_token`/`create_draft_post`/`run()` 시그니처가 전 태스크에서 동일하게 사용됨을 확인. `article`의 `keywords`가 빈 리스트일 때 `search_products` 미호출 처리가 main.py에 반영됨.
