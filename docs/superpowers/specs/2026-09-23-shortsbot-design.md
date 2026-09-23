# AI 뉴스 유튜브 쇼츠 자동화 봇(shortsbot) — Design Spec

**Goal:** blogbot과 같은 AI 뉴스 RSS 풀에서 가장 흥미로운 기사 1건을 골라 30~45초 짜리 유튜브 쇼츠(TTS 나레이션 + AI 이미지 슬라이드 + 자막)로 자동 제작하고, 설명란에 쿠팡/알리 제휴 링크와 텔레그램 채널 링크를 넣어 채널에 바로 공개(public) 업로드한다. **목표는 쇼츠 자체 광고수익이 아니라, 승인 게이트 없이 바로 시작 가능한 제휴/구독 트래픽 퍼널이다.**

**Status:** Approved by user (2026-09-23). 배경: 블로그(Blogger/Tistory) 쪽 수익화가 애드센스 심사·트래픽 0·Ezoic의 서브도메인 미지원 등으로 계속 막혀([[project_revenue_status]]), 승인 게이트가 없는 다른 채널을 시도하기로 함.

---

## 왜 이 구조인가 (핵심 결정 + 근거)

| 결정 | 선택 | 이유 |
|---|---|---|
| 소재 선택 방식 | feeds.txt 후보 기사 중 Claude가 "가장 흥미로운/자극적인 것" 1건을 선택 + 대본 동시 생성 | blogbot과 소스(RSS)는 같지만 선정 기준이 다름(blogbot=최신순, shortsbot=훅 강도). 새 RSS 소스 추가 없이 기존 전문매체 풀에서 바로 시작 가능 |
| 중복 방지 | `shorts_posted_ids.json` 별도 파일 | blogbot과 dedup 상태를 공유하면 같은 기사를 두 채널이 서로 못 다루게 막아버림 — 형식이 다르므로 독립적으로 추적 |
| TTS 엔진 | `edge-tts` (비공식 무료 라이브러리) | 가입/과금 없이 바로 사용 가능, 한국어 음질 양호. 기존 HF 무료 티어 이미지 생성과 같은 "무료 우선" 패턴. 리스크: 마이크로소프트 비공식 엔드포인트라 예고 없이 막힐 수 있음(README에 명시) |
| 영상 조립 | `ffmpeg` CLI 직접 호출(subprocess) | GitHub Actions `ubuntu-latest`에 기본 설치되어 있어 추가 의존성 없음. moviepy 같은 래퍼 라이브러리보다 가볍고 표준적 |
| YouTube 업로드 | `google-api-python-client` (예외적 SDK 사용) | 영상 업로드는 resumable upload 프로토콜(청크 단위, 세션 기반)이라 raw `requests`로 직접 구현하면 복잡도·버그 위험이 큼 — blogbot 설계에서 `feedparser`를 예외 허용한 것과 같은 이유 |
| 발행 방식 | **완전 자동 공개(`privacyStatus: public`)** | blogbot(draft만 생성, 사람이 최종 발행)과 달리 사람 검수 단계 없음 — 사용자가 명시적으로 선택. 오탈자/저품질 영상이 그대로 공개되는 리스크를 감수하기로 함 |
| 콘텐츠 소스 재사용 | blogbot의 `feeds.txt`, `coupang_search.py`, `image_generator.py`를 import로 재사용 | 같은 로직을 두 번 만들지 않음. `coupang_search.py`는 API 키가 아니라 `curated_products.json` 파일 기반이라 재사용에 추가 인증 불필요 |
| 인증 재사용 | 기존 Google OAuth 클라이언트(GOOGLE_CLIENT_ID/SECRET)에 `youtube.upload` 스코프 추가 | 새 Google Cloud 프로젝트 불필요. 단, 스코프가 늘어나므로 refresh_token은 새로 발급받아야 함(혼선 방지 위해 `YOUTUBE_REFRESH_TOKEN`으로 Blogger용과 분리 보관) |

---

## 아키텍처

```
GitHub Actions (매일 1회, blogbot과 다른 시간대 — 예: KST 20:00 = UTC 11:00)
  → rss_reader.py (blogbot 재사용)  : feeds.txt에서 최근 기사 N건(예: 10건) 수집
  → shorts_dedup                    : shorts_posted_ids.json 기준으로 미게시 항목만 후보로 필터
  → script_writer.py                : Claude API 1회 호출
                                       → 후보 중 가장 흥미로운 1건 선택 + 30~45초 대본(문장 4~6개) 작성
                                       → {chosen_link, title, sentences: [str], keywords: [str]}
  → tts.py                          : 문장별 edge-tts 호출 → mp3 파일 리스트
  → image_generator.py (blogbot 재사용) : 문장별 HF 이미지 생성 → 실패 시 고정 기본 이미지로 대체
  → video_assembler.py              : ffmpeg로 문장 단위 (이미지+오디오+번인 자막) 세그먼트 생성 후 concat → mp4
  → coupang_search.py (blogbot 재사용) : keywords[0]로 관련상품 조회 → 설명란용 링크
  → youtube_api.py                  : refresh_token으로 access_token 갱신 → 영상 업로드(public), 제목/설명 첨부
  → shorts_posted_ids.json 갱신 후 git commit/push
```

---

## 컴포넌트 인터페이스

### `config.py`
- `Settings`: `anthropic_api_key`, `google_client_id`, `google_client_secret`, `youtube_refresh_token`, `youtube_channel_id`, `telegram_channel_url`
- `load_settings() -> Settings` — 필수값 누락 시 `RuntimeError`

### `script_writer.py`
- `pick_and_write_script(settings: Settings, candidates: list[dict]) -> dict` — Claude API 1회 호출. `candidates`는 `rss_reader`가 가져온 미게시 기사 리스트(최근 N건). 반환: `{chosen_link: str, title: str, sentences: list[str], keywords: list[str]}`
- 프롬프트 요구사항: 후보 중 가장 흥미/자극적인 것 1개를 고르고, 30~45초 분량 나레이션 대본을 문장 리스트로 작성, JSON 형식으로만 응답
- JSON 파싱 실패 시 `ValueError` — main에서 이번 실행 skip 처리

### `tts.py`
- `synthesize(sentences: list[str], out_dir: str, voice: str = "ko-KR-SunHiNeural") -> list[str]` — 문장별로 `edge-tts` 호출해 mp3 생성, 파일 경로 리스트 반환. 문장 단위 분리는 이미지·자막과 타이밍을 맞추기 위함

### `video_assembler.py`
- `assemble_video(sentences: list[str], audio_paths: list[str], image_paths: list[str], out_path: str) -> str` — 문장별 세그먼트(이미지 정지화면 + 해당 오디오 + `drawtext` 필터로 번인한 자막)를 ffmpeg로 만들고 concat, 최종 mp4 경로 반환. 해상도 1080x1920(세로), 세그먼트 길이는 오디오 길이에 맞춤

### `youtube_api.py`
- `refresh_access_token(settings: Settings) -> str` — blogbot의 `blogger_api.py`와 동일한 방식으로 `https://oauth2.googleapis.com/token`에 POST
- `upload_video(settings: Settings, access_token: str, video_path: str, title: str, description: str) -> str` — `google-api-python-client`의 `MediaFileUpload`로 resumable upload, `privacyStatus="public"`, 업로드된 영상 URL 반환

### `description_builder.py`
- `build_description(script_summary: str, products: list[dict], telegram_url: str, keywords: list[str]) -> str` — 순수 함수. 요약 1~2줄 + 관련상품 링크(있으면) + 텔레그램 링크 + 해시태그 조립

### `main.py`
- `run() -> str | None` — 오케스트레이션. 업로드 성공 시 영상 URL, 신규 기사 없음/전체 실패 시 `None`

---

## 폴더 구조

```
shortsbot/
├── config.py
├── script_writer.py
├── tts.py
├── video_assembler.py
├── youtube_api.py
├── description_builder.py
├── main.py
├── shorts_posted_ids.json     # 런타임 생성, git에 커밋되어 이력 유지
├── requirements.txt           # edge-tts, google-api-python-client, google-auth, python-dotenv, pytest
├── .env.example
├── tests/
│   ├── test_script_writer.py
│   ├── test_tts.py
│   ├── test_video_assembler.py
│   ├── test_youtube_api.py
│   ├── test_description_builder.py
│   └── test_main.py
└── README.md

.github/workflows/shortsbot.yml   # 매일 1회 cron, blogbot과 다른 시간대
```

`blogbot/rss_reader.py`, `blogbot/coupang_search.py`, `blogbot/image_generator.py`, `blogbot/feeds.txt`, `blogbot/curated_products.json`은 새로 만들지 않고 `blogbot` 폴더를 파이썬 경로에 추가해 import/참조로 재사용한다.

---

## 사전 준비 (사람이 직접 — 코드 작업 전)

1. Google Cloud Console에서 YouTube Data API v3 활성화 (Blogger용과 같은 프로젝트 사용 가능)
2. 기존 OAuth 클라이언트 동의 화면에 스코프 `https://www.googleapis.com/auth/youtube.upload` 추가 → 로컬에서 1회 재동의해 새 `refresh_token` 발급(Blogger용과 섞이지 않게 `YOUTUBE_REFRESH_TOKEN`으로 별도 보관)
3. 업로드 대상 유튜브 채널의 `channel_id` 확인
4. 텔레그램 채널 초대 링크 준비
5. `edge-tts`로 한국어 보이스 몇 개 미리 들어보고 최종 voice 선택 (기본값 `ko-KR-SunHiNeural` 제안)

---

## 에러 처리 원칙

- Claude 대본 생성, TTS, 영상 조립, YouTube 업로드 중 하나라도 실패하면 예외를 상위로 전파해 `main.run()`이 로그 남기고 종료(워크플로 실패로 표시, 조용히 삼키지 않음)
- 이미지 생성(HF)만 예외: blogbot과 동일하게 무료 한도 소진 등으로 실패하면 해당 문장에 고정 기본 이미지로 대체하고 계속 진행(영상 제작 자체를 막지 않음)
- 쿠팡 관련상품 매칭 실패는 설명란에서 그 섹션만 생략(전체 실패 사유 아님)

## 테스트 방침

- 순수 로직(`description_builder`, dedup 필터링)은 pytest 직접 테스트
- 외부 호출(Claude, `edge-tts`, `ffmpeg` subprocess, YouTube API)은 `unittest.mock`으로 모킹, 실제 네트워크/외부 프로세스 호출 없이 테스트 — blogbot과 동일 원칙, 추가 mocking 라이브러리 설치 안 함

## 리스크 / 열린 이슈

- **완전 자동 공개**: 사람 검수 단계가 없어 오탈자·부적절 콘텐츠가 그대로 채널에 노출될 수 있음 — 사용자가 명시적으로 감수하기로 선택한 트레이드오프
- **edge-tts 안정성**: 비공식 라이브러리라 마이크로소프트가 예고 없이 엔드포인트를 막을 수 있음 — 막히면 TTS 대체 수단(Google Cloud TTS 등 유료) 검토 필요
- **유튜브 콘텐츠 정책**: 반복적/저가치 자동생성 콘텐츠에 대한 유튜브의 수익화·노출 제한 정책이 있음. 이 프로젝트는 파트너프로그램 수익이 목적이 아니라 링크 클릭 유도가 목적이라 직접적 타격은 작지만, 채널 자체가 추천 알고리즘에서 불이익을 받을 가능성은 있음
- **이미지 생성 리스크**: `image_generator.py`를 그대로 재사용하므로 blogbot에 이미 적용된 실존 인물/로고 묘사 관련 정책이 그대로 적용됨(별도 조치 불필요, 다만 구현 시 프롬프트 재확인 권장)
