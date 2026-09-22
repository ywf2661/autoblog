# AI 블로그 자동 포스팅 봇 — Design Spec

**Goal:** AI(Claude 등) 관련 RSS 피드를 매일 수집해, 원문을 재작성한 블로그 글의 초안(draft)을 Blogger에 자동 생성한다. 글에는 주제 키워드 기반 쿠팡파트너스 관련상품 링크를 삽입한다. 발행(공개)은 사람이 검토 후 수동으로 한다.

**Status:** Approved by user (2026-09-22). Superseded topic: 원래 "티스토리"로 요청받았으나, 티스토리 Open API가 2024년 2월 완전 종료되어(공식 공지 notice.tistory.com/2664) 실행 불가능함을 확인 → **Blogger(Google)로 전환**. 주제도 최초 제안(IT 일반)에서 **AI/Claude 트렌드·활용 팁**으로 확정.

---

## 왜 이 구조인가 (핵심 결정 + 근거)

| 결정 | 선택 | 이유 |
|---|---|---|
| 발행 플랫폼 | Blogger API v3 | 티스토리 API 종료. Blogger는 공식 REST API 유지, 애드센스 네이티브 연동(동일 구글 계정), 서버 비용 0원 |
| 실행 엔진 | GitHub Actions cron + Python | 서버 비용 0원, dealbot과 동일 스택 재사용, 테스트 용이 |
| 콘텐츠 소스 | RSS 요약만 참고해 완전 재작성 | 원문 전문 크롤링은 저작권/언론사 약관 위반 소지. 요약 기반 재작성은 리스크가 낮음 |
| 발행 빈도 | 1일 1건 | 과도한 자동생성 글은 애드센스 "대량 저품질 콘텐츠" 정책 위반 리스크. 소량으로 시작 |
| 발행 방식 | Draft만 자동 생성, 공개는 수동 | 사람 검수 없는 완전 자동 공개는 오탈자·저품질·저작권 사고를 그대로 노출시킬 위험 |
| 글쓰기 AI | Anthropic Claude API | 주제가 Claude/AI라 일관성 있음, 저비용 모델(예: claude-haiku 계열)로 충분 |
| 쿠팡 링크 삽입 | 키워드 검색 기반, 관련상품 1~3개 | 글 내용과 무관한 고정 배너보다 클릭률·사용자 경험이 나음 |
| RSS 파서 | `feedparser` 신규 의존성 | 실전 RSS는 인코딩/네임스페이스가 제각각이라 표준 라이브러리 XML 파서로는 안정적으로 처리하기 어려움. 예외적으로 잘 검증된 라이브러리 사용 |
| Claude/Blogger 호출 | `requests` 직접 호출 (SDK 미사용) | 기존 프로젝트의 최소 의존성 원칙 유지. 둘 다 단순 REST 호출이라 SDK 불필요 |

---

## 아키텍처

```
GitHub Actions (매일 1회, KST 09:00 = UTC 00:00)
  → rss_reader.py      : feeds.txt의 RSS 피드에서 신규 기사(title, summary, link) 수집
  → dedup.py            : posted_ids.json 기준으로 이미 다룬 기사(link 해시) 제외
  → article_writer.py   : Claude API 1회 호출 → {title, body_html, keywords: [str]} 생성
  → coupang_search.py   : keywords[0]로 쿠팡파트너스 상품검색 API 호출 → 상품 1~3개
  → content_assembler.py: body_html + "관련 상품" 섹션 + 원문 출처 링크를 최종 HTML로 조립
  → blogger_api.py      : refresh_token으로 access_token 갱신 → Blogger API로 draft 글 생성
  → dedup 상태(posted_ids.json) 갱신 후 git commit/push
```

하루 발행 개수 1건이므로, `rss_reader`가 모은 신규 기사 중 **가장 최근 1건만** 처리하고 나머지는 다음 실행으로 넘긴다(무시하지 않고 dedup 대상에서 제외한 채로 남겨둠 → 다음날 그 중 가장 최근 것을 다시 후보로 삼음).

---

## 컴포넌트 인터페이스

### `config.py`
- `Settings`: `anthropic_api_key`, `coupang_access_key`, `coupang_secret_key`, `google_client_id`, `google_client_secret`, `google_refresh_token`, `blogger_blog_id`
- `load_settings() -> Settings` — 필수값 누락 시 `RuntimeError`

### `rss_reader.py`
- `fetch_feed_entries(feed_urls: list[str]) -> list[dict]` — 각 dict: `{title, summary, link, published}`. `feedparser.parse()` 래핑, 파싱 실패한 피드는 skip하고 나머지 계속 진행

### `dedup.py`
- `load_posted_ids(path: str) -> set[str]`
- `save_posted_ids(path: str, ids: set[str]) -> None`
- `pick_next_entry(entries: list[dict], posted_ids: set[str]) -> dict | None` — 미게시 항목 중 `published` 최신 1건 반환, 없으면 `None`

### `article_writer.py`
- `write_article(settings: Settings, entry: dict) -> dict` — Claude API 호출, 반환값 `{title: str, body_html: str, keywords: list[str]}`
- 프롬프트 요구사항: 원문 요약만 참고해 완전히 새로운 구성/문장으로 작성, 마지막에 "출처: {link}" 명시, JSON 형식으로만 응답하도록 지시
- Claude 응답이 JSON 파싱 실패 시 `ValueError` — main에서 해당 기사 skip 처리

### `coupang_search.py`
- `search_products(settings: Settings, keyword: str, limit: int = 3) -> list[dict]` — dealbot의 `signing.py`(HMAC 서명) 로직을 그대로 가져와 상품검색 API(`/v2/providers/affiliate_open_api/apis/openapi/products/search`) 호출. 반환 dict: `{productName, productUrl, productImage, productPrice}`
- API 실패/키워드 결과 없음 시 빈 리스트 반환 (전체 실행은 계속 진행, 관련상품 섹션만 생략)
- `main.py`에서 `keywords`가 빈 리스트면 `search_products` 호출 자체를 생략하고 빈 리스트로 취급 (article_writer 프롬프트는 keywords를 최소 1개 포함하도록 지시하지만, 방어적으로 처리)

### `content_assembler.py`
- `assemble_post_html(body_html: str, products: list[dict]) -> str` — 순수 함수, 상품 리스트가 비어있으면 관련상품 섹션 자체를 생략

### `blogger_api.py`
- `refresh_access_token(settings: Settings) -> str` — `https://oauth2.googleapis.com/token`에 refresh_token으로 POST
- `create_draft_post(settings: Settings, access_token: str, title: str, html: str) -> str` — Blogger API `posts.insert(isDraft=true)`, 생성된 post URL(편집용) 반환

### `main.py`
- `run() -> str | None` — 오케스트레이션. 새로 생성한 draft가 있으면 그 URL, 없으면 `None`(신규 기사 없음 또는 전부 실패)

---

## 데이터 흐름 요약

```
feeds.txt → rss_reader → dedup(필터) → 1건 선택
  → article_writer(Claude) → {title, body_html, keywords}
  → coupang_search(keywords[0]) → products
  → content_assembler → 최종 HTML
  → blogger_api(draft 생성)
  → dedup 상태 저장
```

---

## 폴더 구조

```
blogbot/
├── config.py
├── rss_reader.py
├── dedup.py
├── article_writer.py
├── coupang_search.py
├── content_assembler.py
├── blogger_api.py
├── main.py
├── feeds.txt                 # AI 관련 RSS URL 목록 (줄바꿈 구분)
├── posted_ids.json           # 런타임 생성, git에 커밋되어 이력 유지
├── requirements.txt          # feedparser, requests, python-dotenv, pytest
├── .env.example
├── tests/
│   ├── test_dedup.py
│   ├── test_rss_reader.py
│   ├── test_article_writer.py
│   ├── test_coupang_search.py
│   ├── test_content_assembler.py
│   ├── test_blogger_api.py
│   └── test_main.py
└── README.md

.github/workflows/blogbot.yml   # 매일 1회 cron
```

dealbot(별도 계획, 루트 파일 예정)과 모듈명 충돌 방지를 위해 `blogbot/` 하위로 격리한다.

---

## 사전 준비 (Task 1, 사람이 직접 — 코드 작업 전)

1. Blogger 블로그 생성, 애드센스 연결/승인 신청
2. Google Cloud Console에서 OAuth 2.0 클라이언트(데스크톱 앱) 생성 → `client_id`/`client_secret` 발급
3. 로컬에서 1회 OAuth 동의 화면을 통해 `refresh_token` 획득 (Blogger API scope: `https://www.googleapis.com/auth/blogger`)
4. Anthropic API 키 발급
5. 쿠팡파트너스 키 (dealbot에서 이미 발급했다면 재사용)
6. `feeds.txt`에 AI 관련 RSS 주소 채우기

---

## 에러 처리 원칙

- 외부 API(Claude/쿠팡/구글) 실패는 해당 단계만 실패 처리하고 예외를 상위로 전파, `main.run()`이 최상위에서 로그 남기고 종료(전체 워크플로 실패로 표시 — 조용히 삼키지 않음). 단, 쿠팡 상품검색 실패는 예외로, "관련상품 없음"으로 진행(상품 추천은 부가 기능이라 전체 실패 사유가 아님)
- RSS 피드 중 일부 파싱 실패는 나머지 피드로 계속 진행

## 테스트 방침

- 순수 로직(`dedup`, `content_assembler`, `pick_next_entry`)은 pytest 직접 테스트
- 외부 API 호출(`rss_reader`의 feedparser, `article_writer`의 Claude, `coupang_search`, `blogger_api`)는 `unittest.mock`으로 모킹, 실제 네트워크 호출 없이 테스트
- dealbot과 동일하게 추가 mocking 라이브러리는 설치하지 않음

## 리스크 / 열린 이슈 (구현 계획에는 포함하되 사용자가 인지해야 할 사항)

- **애드센스 정책:** AI 생성 콘텐츠라도 "독창적 가치"가 있어야 함(2024년 스팸 정책 업데이트 기준). 요약 재작성 + 사람 검수 단계로 최소한의 안전장치는 있으나, 애드센스 심사/유지 여부를 보장할 수 없음
- **저작권:** 재작성이라도 원문 구조를 과도하게 따라가면 분쟁 소지 있음 — 프롬프트에서 "구성 자체를 새로 설계"하도록 명시할 것
- **Blogger refresh_token 만료:** 6개월 이상 미사용 시 구글이 refresh_token을 만료시킬 수 있음(테스트 상태 OAuth 앱의 경우 7일). OAuth 동의 화면을 "게시" 상태로 전환하거나 주기적 확인 필요 — 구현 시 README에 명시
