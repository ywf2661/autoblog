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
