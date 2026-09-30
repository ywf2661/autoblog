import html
import os
import time

import requests

from config import Settings

# ponytail: 모델 경로·요청 스키마는 Higgsfield가 바꿀 수 있음 —
# https://docs.higgsfield.ai/docs/llms.txt 에서 현재 스키마 확인 후 갱신할 것.
API_BASE = "https://api.higgsfield.ai"
MODEL = "higgsfield-ai/soul/v2/standard"
POLL_INTERVAL_SEC = 3
POLL_TIMEOUT_SEC = 180

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/ywf2661/autoblog/master/blogbot"


def generate_image(settings: Settings, prompt: str, aspect_ratio: str = "16:9") -> bytes | None:
    """Higgsfield로 이미지를 생성해 원본 bytes를 반환한다. 키가 없거나 실패하면 None."""
    if not settings.higgsfield_api_key:
        return None
    headers = {"Authorization": f"Key {settings.higgsfield_api_key}"}
    try:
        response = requests.post(
            f"{API_BASE}/{MODEL}",
            headers=headers,
            json={"prompt": prompt, "aspect_ratio": aspect_ratio, "resolution": "1k"},
            timeout=30,
        )
        response.raise_for_status()
        status_url = response.json()["status_url"]

        deadline = time.monotonic() + POLL_TIMEOUT_SEC
        while time.monotonic() < deadline:
            result = requests.get(status_url, headers=headers, timeout=30)
            result.raise_for_status()
            data = result.json()
            status = data.get("status")
            if status == "completed":
                image = requests.get(data["images"][0]["url"], timeout=60)
                image.raise_for_status()
                return image.content
            if status in ("failed", "nsfw", "cancelled"):
                print(f"이미지 생성 실패({status}), 건너뜀: {data}")
                return None
            time.sleep(POLL_INTERVAL_SEC)
        print(f"이미지 생성 시간 초과({POLL_TIMEOUT_SEC}s), 건너뜀: {status_url}")
        return None
    except requests.RequestException as e:
        body_text = e.response.text if e.response is not None else "(응답 없음)"
        print(f"이미지 생성 요청 실패, 건너뜀: {e} / 응답: {body_text}")
        return None
    except (KeyError, IndexError, ValueError) as e:
        print(f"이미지 생성 응답 형식이 예상과 다름, 건너뜀: {e!r}")
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
