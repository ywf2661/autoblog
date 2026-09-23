# AI 뉴스 유튜브 쇼츠 자동화 봇

blogbot과 같은 AI 뉴스 RSS 풀에서 가장 흥미로운 기사 1건을 골라 TTS 나레이션 + AI 이미지 슬라이드 + 자막으로
30~45초 세로 영상을 만들어 유튜브에 **바로 공개(public) 업로드**합니다. 설명란에 쿠팡 관련상품·텔레그램 채널
링크를 넣어 트래픽 퍼널로 씁니다. (자세한 배경: `docs/superpowers/specs/2026-09-23-shortsbot-design.md`)

## 로컬 실행

1. `cd shortsbot && pip install -r requirements.txt`
2. `.env.example`을 `.env`로 복사 후 값 채우기
3. `python main.py`

## 환경변수

| 이름 | 설명 |
|---|---|
| ANTHROPIC_API_KEY | Anthropic API 키 (blogbot과 공용 가능) |
| GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET | blogbot과 같은 OAuth 클라이언트 재사용 가능 |
| YOUTUBE_REFRESH_TOKEN | `youtube.upload` 스코프로 새로 재동의해서 받은 refresh token — blogbot의 GOOGLE_REFRESH_TOKEN과 다름 |
| YOUTUBE_CHANNEL_ID | 업로드 대상 채널 ID |
| TELEGRAM_CHANNEL_URL | 설명란에 넣을 텔레그램 채널 초대 링크 |
| HF_API_KEY | 선택 — 없으면 이미지 대신 단색 배경으로 대체 |

## 사전 준비

1. Google Cloud Console에서 YouTube Data API v3 활성화 (blogbot과 같은 프로젝트 사용 가능)
2. 기존 OAuth 클라이언트 동의 화면에 스코프 `https://www.googleapis.com/auth/youtube.upload` 추가 →
   로컬에서 1회 재동의해 `YOUTUBE_REFRESH_TOKEN` 새로 발급
3. 업로드 대상 채널의 `channel_id` 확인
4. 텔레그램 채널 초대 링크 준비

## 주의사항

- **완전 자동 공개**: draft 없이 바로 `public`으로 업로드됩니다. 오탈자/저품질 영상이 그대로 노출될 수 있음을
  감수하는 구조입니다.
- **edge-tts는 비공식 라이브러리**: 마이크로소프트가 예고 없이 막을 수 있습니다. 막히면 README의 TTS 엔진을
  교체해야 합니다.
- ffmpeg는 워크플로에서 `apt-get install`로 직접 설치합니다(`ubuntu-latest`에 기본 설치되어 있지 않음 —
  실제로 겪은 문제). 로컬 실행 시에도 직접 설치 필요합니다.

## 테스트

`cd shortsbot && python -m pytest -v`
