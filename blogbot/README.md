# AI 블로그 자동 포스팅 봇

AI(Claude 등) 관련 RSS 피드를 매일 1건 확인해 Claude로 재작성하고, 쿠팡파트너스 관련상품 링크를 붙여 Blogger에 임시저장(draft) 글을 생성합니다. 공개 발행은 Blogger 대시보드에서 사람이 직접 합니다.

## 로컬 실행

1. `cd blogbot && pip install -r requirements.txt`
2. `.env.example`을 `.env`로 복사 후 값 채우기 (계정/키 준비는 상위 plan의 Task 1 참고)
3. `feeds.txt`에 사용할 RSS 주소 확인/수정
4. `curated_products.json`에 쿠팡파트너스 링크 채우기 (아래 "관련상품 링크" 참고)
5. `python main.py`

## 환경변수

| 이름 | 설명 |
|---|---|
| ANTHROPIC_API_KEY | Anthropic API 키 |
| GOOGLE_CLIENT_ID | Google OAuth 클라이언트 ID (데스크톱 앱) |
| GOOGLE_CLIENT_SECRET | Google OAuth 클라이언트 secret |
| GOOGLE_REFRESH_TOKEN | 1회 OAuth 동의로 발급받은 refresh token |
| BLOGGER_BLOG_ID | 대상 Blogger 블로그 ID |

## 배포

GitHub Actions가 매일 1회 자동 실행(`.github/workflows/blogbot.yml`, UTC 00:00 = KST 09:00). 저장소 Secrets에 위 5개 값 등록 필요.

## 발행 흐름

1. `feeds.txt`의 RSS에서 아직 다루지 않은 기사 중 가장 최근 1건 선택
2. Claude API로 완전히 새로 작성 (원문 요약만 참고, 전문 미사용)
3. 글 키워드로 `curated_products.json`에서 관련상품 조회 후 본문에 섹션 추가
4. Blogger에 **draft(임시저장)**로 생성 — 공개 발행은 수동으로 Blogger 대시보드에서 진행
5. 같은 제목+HTML을 `tistory_drafts/`에 파일로도 저장 — 티스토리는 공식 posting API가 없어서(2024.02 종료) 자동 발행이 불가능하므로, 이 파일을 열어 제목/본문을 티스토리 글쓰기 화면에 직접 복붙해서 발행
6. 처리한 기사는 `posted_ids.json`에 기록해 중복 방지

## 관련상품 링크 (`curated_products.json`)

쿠팡파트너스 오픈API는 누적 판매 15만원 이상 + 최종승인 후에만 발급되지만, **파트너스 링크 자체는 가입 즉시 대시보드에서 수동으로 만들 수 있고 바로 수익이 발생**합니다. 그래서 이 봇은 API 대신 직접 만든 링크를 파일에 저장해두고 씁니다.

1. 쿠팡파트너스 사이트에서 상품 검색 → "링크 생성" → URL 복사
2. `curated_products.json`에 카테고리별로 추가:

```json
{
  "노트북": [
    {"productName": "상품명", "productUrl": "https://link.coupang.com/...", "productImage": "https://...", "productPrice": 1000000}
  ],
  "기본": [
    {"productName": "매칭 안 될 때 보여줄 기본 상품", "productUrl": "...", "productImage": "...", "productPrice": 0}
  ]
}
```

글에서 뽑힌 키워드와 카테고리 이름이 부분일치하면 그 카테고리 상품을, 매칭이 없으면 `기본` 카테고리를, 그마저 없으면 관련상품 섹션 없이 발행됩니다. **본인이 만든 링크를 본인이 클릭·구매하는 행위는 쿠팡파트너스 약관 위반(계정정지 사유)이니 하지 마세요.**

## 주의사항

- Google OAuth 동의 화면이 "테스트" 상태면 refresh_token이 7일 후 만료될 수 있습니다. Cloud Console에서 "게시" 상태로 전환하세요.
- 애드센스는 저품질/대량 자동생성 콘텐츠에 대한 정책이 있습니다. draft를 반드시 검토 후 발행하세요.

## 테스트

`cd blogbot && pytest -v`
