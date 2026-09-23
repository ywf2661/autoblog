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
요약 문장을 그대로 늘어놓지 말고, 배경 설명·맥락·독자에게 도움될 만한 관점을 스스로 보강해 최소 1500자 이상 분량으로 작성하라.
<h3> 소제목 2~3개로 문단을 나눠 구성하라.
본문 중 자연스러운 두 지점(예: 첫 소제목 문단과 중간 소제목 문단)에 [IMAGE_1], [IMAGE_2] 자리표시자를 각각 한 번씩 넣어라.
각 자리표시자에 어울리는 삽화를 묘사하는 이미지 생성 프롬프트를 image_prompts에 순서대로 넣어라 (사진이 아닌 삽화/일러스트 스타일로 묘사할 것 — 실존 인물·브랜드 로고를 특정하지 말 것).
글 마지막에는 "출처: {link}" 문구를 포함하라.
블로그 글과 어울리는, 쿠팡에서 검색할 수 있는 실존 상품 카테고리 키워드를 1~2개 뽑아라 (예: "노트북", "블루투스 이어폰").

다음 JSON 형식으로만 응답하라. 다른 텍스트는 포함하지 마라:
{{"title": "블로그 글 제목", "body_html": "<h3>...</h3><p>...[IMAGE_1]...</p><h3>...</h3><p>...[IMAGE_2]...</p>", "keywords": ["키워드1"], "image_prompts": ["삽화 프롬프트1", "삽화 프롬프트2"]}}
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
            "max_tokens": 4000,
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "{"},
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    response_body = response.json()
    try:
        text = response_body["content"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Claude 응답 구조 오류: {response_body!r}") from e
    try:
        result = json.loads("{" + text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude 응답이 JSON이 아님: {text!r}") from e

    if "title" not in result or "body_html" not in result:
        raise ValueError(f"Claude 응답에 필수 필드 누락: {result!r}")
    result.setdefault("keywords", [])
    result.setdefault("image_prompts", [])
    return result
