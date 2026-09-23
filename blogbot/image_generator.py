import base64
import html
import os

import requests

from config import Settings

# ponytail: 모델명은 Gemini API 이미지 생성 모델이 바뀌면 깨질 수 있음 —
# AI Studio에서 현재 사용 가능한 이미지 생성 모델명으로 갱신할 것.
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MODEL = "gemini-2.5-flash-image"

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/ywf2661/autoblog/master/blogbot"


def generate_image(settings: Settings, prompt: str) -> bytes | None:
    """프롬프트로 이미지를 생성해 원본 bytes를 반환한다. 키가 없거나 실패하면 None."""
    if not settings.gemini_api_key:
        return None
    try:
        response = requests.post(
            API_URL.format(model=MODEL),
            headers={
                "x-goog-api-key": settings.gemini_api_key,
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
            },
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
        parts = body["candidates"][0]["content"]["parts"]
        for part in parts:
            # 문서마다 camelCase/snake_case가 섞여 있어 둘 다 확인
            inline = part.get("inlineData") or part.get("inline_data")
            if inline:
                return base64.b64decode(inline["data"])
        print(f"이미지 생성 응답에 이미지 파트 없음, 건너뜀: {body!r}")
        return None
    except requests.RequestException as e:
        body_text = e.response.text if e.response is not None else "(응답 없음)"
        print(f"이미지 생성 요청 실패, 건너뜀: {e} / 응답: {body_text}")
        return None
    except (KeyError, IndexError, ValueError, TypeError) as e:
        print(f"이미지 생성 응답 파싱 실패, 건너뜀: {e}")
        return None


def save_generated_image(dir_path: str, filename: str, data: bytes) -> str:
    """이미지를 파일로 저장하고 경로를 반환한다."""
    os.makedirs(dir_path, exist_ok=True)
    path = os.path.join(dir_path, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path


def raw_image_url(dir_name: str, filename: str) -> str:
    return f"{GITHUB_RAW_BASE}/{dir_name}/{filename}"


def insert_images(body_html: str, image_urls: list[str | None]) -> str:
    """본문의 [IMAGE_N] 플레이스홀더를 이미지 태그로 치환한다. URL이 없으면 제거."""
    result = body_html
    for i, url in enumerate(image_urls, start=1):
        placeholder = f"[IMAGE_{i}]"
        replacement = (
            f'<img src="{html.escape(url)}" alt="" style="max-width:100%">' if url else ""
        )
        result = result.replace(placeholder, replacement)
    return result
