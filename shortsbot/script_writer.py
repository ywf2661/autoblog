import json

import requests

from config import Settings

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"

PROMPT_TEMPLATE = """다음은 오늘 아직 다루지 않은 AI 관련 뉴스 기사 후보들이다.

{candidate_list}

이 중에서 유튜브 쇼츠 시청자가 가장 흥미롭고 자극적으로 느낄 만한 기사 1개를 골라라.
고른 기사를 바탕으로 30~45초 분량(문장 4~6개)의 한국어 나레이션 대본을 작성하라.
각 문장은 그 자체로 한 화면(이미지 1장)에 어울리는 길이로 끊어라.
쇼츠와 어울리는, 쿠팡에서 검색할 수 있는 실존 상품 카테고리 키워드를 1~2개 뽑아라 (예: "노트북", "블루투스 이어폰").

다음 JSON 형식으로만 응답하라. 다른 텍스트는 포함하지 마라:
{{"chosen_index": 0, "title": "쇼츠 제목", "sentences": ["문장1", "문장2"], "keywords": ["키워드1"]}}
"""


def _format_candidates(candidates: list[dict]) -> str:
    return "\n".join(
        f"{i}. 제목: {c['title']}\n   요약: {c['summary']}"
        for i, c in enumerate(candidates)
    )


def pick_and_write_script(settings: Settings, candidates: list[dict]) -> dict:
    """후보 기사 중 하나를 골라 쇼츠 대본을 작성한다."""
    prompt = PROMPT_TEMPLATE.format(candidate_list=_format_candidates(candidates))
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

    required = ("chosen_index", "title", "sentences")
    if any(key not in result for key in required):
        raise ValueError(f"Claude 응답에 필수 필드 누락: {result!r}")

    index = result["chosen_index"]
    if not isinstance(index, int) or not (0 <= index < len(candidates)):
        raise ValueError(f"chosen_index가 후보 범위를 벗어남: {index!r}")

    result["chosen_link"] = candidates[index]["link"]
    result.setdefault("keywords", [])
    return result
