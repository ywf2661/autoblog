# AI 뉴스 유튜브 쇼츠 자동화 봇(shortsbot) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** blogbot과 같은 AI 뉴스 RSS 풀에서 가장 흥미로운 기사 1건을 골라 TTS 나레이션 + AI 이미지 슬라이드 + 자막으로 30~45초 세로 영상을 만들어 유튜브에 바로 공개(public) 업로드하고, 설명란에 쿠팡 관련상품·텔레그램 채널 링크를 넣는다.

**Architecture:** `shortsbot/`을 `blogbot/`과 나란히 만든다. `blogbot/rss_reader.py`, `coupang_search.py`, `image_generator.py`, `dedup.py`는 새 `blogbot_bridge.py`를 통해 그대로 import해 재사용(코드 복사 없음). 새로 만드는 것은 대본 생성(Claude), TTS(edge-tts), 영상 조립(ffmpeg subprocess), 유튜브 업로드(google-api-python-client) 네 모듈과 이를 묶는 `main.py`.

**Tech Stack:** Python 3.11, `requests`, `feedparser`(재사용 경로로 간접 필요), `edge-tts`, `google-api-python-client`, `google-auth`, `ffmpeg`(CLI, subprocess 호출), pytest + `unittest.mock`

**Spec:** [docs/superpowers/specs/2026-09-23-shortsbot-design.md](../specs/2026-09-23-shortsbot-design.md)

## Global Constraints

- Python 3.11, GitHub Actions `ubuntu-latest`에서 실행 (ffmpeg 기본 설치되어 있음, 별도 설치 스텝 불필요)
- SDK/래퍼 라이브러리 원칙적으로 지양, `requests` 직접 호출 우선 — 단 `google-api-python-client`는 유튜브 resumable upload 구현 복잡도 때문에 예외 허용(스펙의 `feedparser` 예외와 동일한 논리)
- 영상 조립은 `ffmpeg` CLI를 `subprocess`로 직접 호출, moviepy 등 래퍼 라이브러리 금지
- TTS는 `edge-tts`(무료)만 사용, 유료 TTS 도입 금지
- 업로드는 항상 `privacyStatus: "public"` — draft/review 단계 없음(사용자가 명시적으로 선택한 트레이드오프)
- 중복 방지는 `shorts_posted_ids.json`을 별도로 쓰며 blogbot의 `posted_ids.json`과 절대 공유하지 않음
- `blogbot/rss_reader.py`, `coupang_search.py`, `image_generator.py`, `dedup.py`는 수정하지 않고 `blogbot_bridge.py`를 통해서만 재사용
- 테스트는 `unittest.mock`만 사용, 추가 mocking 라이브러리 설치 금지

## Review Focus

- 후보 기사가 전부 이미 게시됨(0건) → `main.run()`이 `None`을 반환하고 Claude/TTS/ffmpeg/YouTube 어느 것도 호출하지 않아야 함 (Task 8)
- 문장 수와 오디오/이미지 파일 수가 안 맞으면 `video_assembler`가 명확한 `ValueError`로 실패해야 함(조용히 잘리거나 인덱스 에러로 죽으면 안 됨) (Task 5)
- `edge-tts` 실패는 예외로 전체 실행을 중단해야 함(이미지 생성 실패처럼 조용히 넘어가면 안 됨 — 스펙의 에러 처리 원칙) (Task 4)
- 유튜브 업로드가 실패하면 `shorts_posted_ids.json`에 기록되면 안 됨(그래야 다음 실행에서 같은 기사로 재시도 가능) (Task 8)
- 관련상품이 하나도 없을 때 설명란에 빈 "관련 상품" 섹션이 남으면 안 됨 (Task 6)

---

## Task 1: 프로젝트 스캐폴딩 + `config.py`

**Files:**
- Create: `shortsbot/requirements.txt`
- Create: `shortsbot/.env.example`
- Create: `shortsbot/config.py`
- Test: `shortsbot/tests/test_config.py`

**Interfaces:**
- Produces: `Settings` dataclass(`anthropic_api_key, google_client_id, google_client_secret, youtube_refresh_token, youtube_channel_id, telegram_channel_url, hf_api_key=""`), `load_settings() -> Settings`

- [ ] **Step 1: 디렉터리와 의존성 파일 생성**

`shortsbot/requirements.txt`:
```
requests
python-dotenv
feedparser
edge-tts
google-api-python-client
google-auth
pytest
```

`shortsbot/.env.example`:
```
ANTHROPIC_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=
YOUTUBE_CHANNEL_ID=
TELEGRAM_CHANNEL_URL=
HF_API_KEY=
```

- [ ] **Step 2: 의존성 설치**

Run: `cd shortsbot && pip install -r requirements.txt`

- [ ] **Step 3: 실패하는 테스트 작성**

`shortsbot/tests/test_config.py`:
```python
import pytest

from config import load_settings


def test_load_settings_raises_when_keys_missing(monkeypatch):
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)
    for key in [
        "ANTHROPIC_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "YOUTUBE_REFRESH_TOKEN",
        "YOUTUBE_CHANNEL_ID",
        "TELEGRAM_CHANNEL_URL",
    ]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError, match="필수 환경변수 누락"):
        load_settings()


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ak")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "gcid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "gcs")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "yrt")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID", "chan123")
    monkeypatch.setenv("TELEGRAM_CHANNEL_URL", "https://t.me/x")

    settings = load_settings()

    assert settings.anthropic_api_key == "ak"
    assert settings.youtube_channel_id == "chan123"
    assert settings.hf_api_key == ""
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `cd shortsbot && python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 5: 구현**

`shortsbot/config.py`:
```python
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    anthropic_api_key: str
    google_client_id: str
    google_client_secret: str
    youtube_refresh_token: str
    youtube_channel_id: str
    telegram_channel_url: str
    # ponytail: hf_api_key 필드명은 blogbot/image_generator.py가 재사용 시
    # sys.path 순서 때문에 이 Settings를 받게 됨(blogbot_bridge.py 참고) —
    # 필드명을 바꾸면 image_generator.generate_image()가 깨짐
    hf_api_key: str = ""


def load_settings() -> Settings:
    load_dotenv()
    required = [
        "ANTHROPIC_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "YOUTUBE_REFRESH_TOKEN",
        "YOUTUBE_CHANNEL_ID",
        "TELEGRAM_CHANNEL_URL",
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"필수 환경변수 누락: {', '.join(missing)}")

    return Settings(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        google_client_id=os.environ["GOOGLE_CLIENT_ID"],
        google_client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        youtube_refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        youtube_channel_id=os.environ["YOUTUBE_CHANNEL_ID"],
        telegram_channel_url=os.environ["TELEGRAM_CHANNEL_URL"],
        hf_api_key=os.getenv("HF_API_KEY", ""),
    )
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd shortsbot && python -m pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: 커밋**

```bash
git add shortsbot/requirements.txt shortsbot/.env.example shortsbot/config.py shortsbot/tests/test_config.py
git commit -m "feat(shortsbot): add project scaffolding and config"
```

---

## Task 2: `blogbot_bridge.py` — blogbot 모듈 재사용 브릿지

**Files:**
- Create: `shortsbot/blogbot_bridge.py`
- Test: `shortsbot/tests/test_blogbot_bridge.py`

**Interfaces:**
- Consumes: `blogbot/rss_reader.fetch_feed_entries`, `blogbot/image_generator.generate_image`, `blogbot/image_generator.save_generated_image`, `blogbot/dedup.hash_link`, `blogbot/dedup.load_posted_ids`, `blogbot/dedup.save_posted_ids`, `blogbot/coupang_search.search_products`(내부용, 직접 노출 안 함)
- Produces: `BLOGBOT_DIR: str`, `fetch_feed_entries`, `generate_image`, `save_generated_image`, `hash_link`, `load_posted_ids`, `save_posted_ids` (모두 재노출), `search_products(keyword: str, limit: int = 3) -> list[dict]`

- [ ] **Step 1: 실패하는 테스트 작성**

`shortsbot/tests/test_blogbot_bridge.py`:
```python
import json
import sys

import blogbot_bridge


def test_blogbot_dir_is_sibling_of_shortsbot_and_on_syspath():
    assert blogbot_bridge.BLOGBOT_DIR.endswith("blogbot")
    assert blogbot_bridge.BLOGBOT_DIR in sys.path


def test_reexports_blogbot_functions():
    assert callable(blogbot_bridge.fetch_feed_entries)
    assert callable(blogbot_bridge.generate_image)
    assert callable(blogbot_bridge.save_generated_image)
    assert callable(blogbot_bridge.hash_link)
    assert callable(blogbot_bridge.load_posted_ids)
    assert callable(blogbot_bridge.save_posted_ids)


def test_search_products_reads_blogbot_curated_catalog(tmp_path, monkeypatch):
    catalog_path = tmp_path / "curated_products.json"
    catalog_path.write_text(
        json.dumps(
            {
                "노트북": [
                    {
                        "productName": "노트북 A",
                        "productUrl": "http://x",
                        "productImage": "http://img",
                        "productPrice": 1000000,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        blogbot_bridge._coupang_search, "CURATED_PRODUCTS_PATH", str(catalog_path)
    )

    result = blogbot_bridge.search_products("최신 노트북 추천")

    assert len(result) == 1
    assert result[0]["productName"] == "노트북 A"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd shortsbot && python -m pytest tests/test_blogbot_bridge.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'blogbot_bridge'`

- [ ] **Step 3: 구현**

`shortsbot/blogbot_bridge.py`:
```python
import os
import sys

_SHORTSBOT_DIR = os.path.dirname(os.path.abspath(__file__))
BLOGBOT_DIR = os.path.join(os.path.dirname(_SHORTSBOT_DIR), "blogbot")
if BLOGBOT_DIR not in sys.path:
    sys.path.append(BLOGBOT_DIR)

from rss_reader import fetch_feed_entries  # noqa: E402
from image_generator import generate_image, save_generated_image  # noqa: E402
from dedup import hash_link, load_posted_ids, save_posted_ids  # noqa: E402
import coupang_search as _coupang_search  # noqa: E402

_coupang_search.CURATED_PRODUCTS_PATH = os.path.join(BLOGBOT_DIR, "curated_products.json")


def search_products(keyword: str, limit: int = 3) -> list[dict]:
    """blogbot의 curated_products.json을 기준으로 관련상품을 조회한다."""
    return _coupang_search.search_products(keyword, limit)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd shortsbot && python -m pytest tests/test_blogbot_bridge.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add shortsbot/blogbot_bridge.py shortsbot/tests/test_blogbot_bridge.py
git commit -m "feat(shortsbot): bridge blogbot's rss/image/dedup/coupang modules"
```

---

## Task 3: `script_writer.py` — Claude로 소재 선택 + 대본 생성

**Files:**
- Create: `shortsbot/script_writer.py`
- Test: `shortsbot/tests/test_script_writer.py`

**Interfaces:**
- Consumes: `config.Settings`
- Produces: `pick_and_write_script(settings: Settings, candidates: list[dict]) -> dict` — 반환 `{chosen_link: str, title: str, sentences: list[str], keywords: list[str]}`. `candidates`의 각 원소는 `{title, summary, link, published}` (blogbot의 `rss_reader` 출력과 동일 형태)

- [ ] **Step 1: 실패하는 테스트 작성**

`shortsbot/tests/test_script_writer.py`:
```python
from unittest.mock import MagicMock, patch

import pytest

from script_writer import pick_and_write_script
from config import Settings


def _settings():
    return Settings("ak", "gcid", "gcs", "yrt", "chan123", "https://t.me/x")


def _candidates():
    return [
        {"title": "기사1", "summary": "요약1", "link": "http://a", "published": (2026, 9, 23)},
        {"title": "기사2", "summary": "요약2", "link": "http://b", "published": (2026, 9, 23)},
    ]


@patch("script_writer.requests.post")
def test_pick_and_write_script_parses_chosen_candidate(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "content": [
            {
                "text": (
                    '"chosen_index": 1, "title": "쇼츠 제목", '
                    '"sentences": ["문장1", "문장2"], "keywords": ["노트북"]}'
                )
            }
        ]
    }
    mock_post.return_value = mock_response

    result = pick_and_write_script(_settings(), _candidates())

    assert result["chosen_link"] == "http://b"
    assert result["title"] == "쇼츠 제목"
    assert result["sentences"] == ["문장1", "문장2"]
    assert result["keywords"] == ["노트북"]


@patch("script_writer.requests.post")
def test_pick_and_write_script_raises_on_invalid_json(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"content": [{"text": "이건 JSON이 아님"}]}
    mock_post.return_value = mock_response

    with pytest.raises(ValueError):
        pick_and_write_script(_settings(), _candidates())


@patch("script_writer.requests.post")
def test_pick_and_write_script_raises_when_chosen_index_out_of_range(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "content": [
            {"text": '"chosen_index": 5, "title": "t", "sentences": ["s"]}'}
        ]
    }
    mock_post.return_value = mock_response

    with pytest.raises(ValueError, match="범위를 벗어남"):
        pick_and_write_script(_settings(), _candidates())


@patch("script_writer.requests.post")
def test_pick_and_write_script_defaults_keywords_when_missing(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "content": [{"text": '"chosen_index": 0, "title": "t", "sentences": ["s"]}'}]
    }
    mock_post.return_value = mock_response

    result = pick_and_write_script(_settings(), _candidates())

    assert result["keywords"] == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd shortsbot && python -m pytest tests/test_script_writer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'script_writer'`

- [ ] **Step 3: 구현**

`shortsbot/script_writer.py`:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd shortsbot && python -m pytest tests/test_script_writer.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add shortsbot/script_writer.py shortsbot/tests/test_script_writer.py
git commit -m "feat(shortsbot): add Claude-based topic pick and script writer"
```

---

## Task 4: `tts.py` — edge-tts 음성 합성

**Files:**
- Create: `shortsbot/tts.py`
- Test: `shortsbot/tests/test_tts.py`

**Interfaces:**
- Produces: `synthesize(sentences: list[str], out_dir: str, voice: str = "ko-KR-SunHiNeural") -> list[str]` — 문장 개수와 같은 길이의 mp3 파일 경로 리스트 반환

- [ ] **Step 1: 실패하는 테스트 작성**

`shortsbot/tests/test_tts.py`:
```python
import os
from unittest.mock import AsyncMock, patch

import pytest

from tts import synthesize


@patch("tts._synthesize_one", new_callable=AsyncMock)
def test_synthesize_creates_one_path_per_sentence(mock_synth, tmp_path):
    paths = synthesize(["문장1", "문장2"], str(tmp_path))

    assert paths == [
        str(tmp_path / "1.mp3"),
        str(tmp_path / "2.mp3"),
    ]
    assert mock_synth.call_count == 2
    mock_synth.assert_any_call("문장1", str(tmp_path / "1.mp3"), "ko-KR-SunHiNeural")
    mock_synth.assert_any_call("문장2", str(tmp_path / "2.mp3"), "ko-KR-SunHiNeural")


@patch("tts._synthesize_one", new_callable=AsyncMock)
def test_synthesize_propagates_errors(mock_synth, tmp_path):
    mock_synth.side_effect = RuntimeError("network down")

    with pytest.raises(RuntimeError):
        synthesize(["문장1"], str(tmp_path))


@patch("tts._synthesize_one", new_callable=AsyncMock)
def test_synthesize_creates_out_dir(mock_synth, tmp_path):
    out_dir = tmp_path / "nested" / "dir"

    synthesize(["문장1"], str(out_dir))

    assert os.path.isdir(out_dir)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd shortsbot && python -m pytest tests/test_tts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tts'`

- [ ] **Step 3: 구현**

`shortsbot/tts.py`:
```python
import asyncio
import os

import edge_tts

DEFAULT_VOICE = "ko-KR-SunHiNeural"


async def _synthesize_one(text: str, path: str, voice: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)


def synthesize(sentences: list[str], out_dir: str, voice: str = DEFAULT_VOICE) -> list[str]:
    """문장별로 음성 파일을 생성하고 경로 리스트를 반환한다. 실패 시 예외를 그대로 전파한다."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, sentence in enumerate(sentences, start=1):
        path = os.path.join(out_dir, f"{i}.mp3")
        asyncio.run(_synthesize_one(sentence, path, voice))
        paths.append(path)
    return paths
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd shortsbot && python -m pytest tests/test_tts.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add shortsbot/tts.py shortsbot/tests/test_tts.py
git commit -m "feat(shortsbot): add edge-tts based narration synthesis"
```

---

## Task 5: `video_assembler.py` — ffmpeg로 영상 조립

**Files:**
- Create: `shortsbot/video_assembler.py`
- Test: `shortsbot/tests/test_video_assembler.py`

**Interfaces:**
- Produces: `assemble_video(sentences: list[str], audio_paths: list[str], image_paths: list[str | None], out_path: str) -> str` — 세 리스트 길이가 다르면 `ValueError`. `image_paths` 원소가 `None`이면 단색 배경으로 대체

- [ ] **Step 1: 실패하는 테스트 작성**

`shortsbot/tests/test_video_assembler.py`:
```python
from unittest.mock import patch

import pytest

from video_assembler import assemble_video


@patch("video_assembler.subprocess.run")
def test_assemble_video_raises_on_length_mismatch(mock_run, tmp_path):
    with pytest.raises(ValueError, match="일치하지 않음"):
        assemble_video(
            ["문장1", "문장2"], ["a1.mp3"], ["i1.png", "i2.png"], str(tmp_path / "out.mp4")
        )

    mock_run.assert_not_called()


@patch("video_assembler.subprocess.run")
def test_assemble_video_builds_one_segment_per_sentence_and_concats(mock_run, tmp_path):
    out_path = str(tmp_path / "out.mp4")

    result = assemble_video(
        ["문장1", "문장2"], ["a1.mp3", "a2.mp3"], ["i1.png", "i2.png"], out_path
    )

    assert result == out_path
    # 세그먼트 2개 + concat 1개 = ffmpeg 총 3번 호출
    assert mock_run.call_count == 3
    for call in mock_run.call_args_list:
        assert call.kwargs["check"] is True


@patch("video_assembler.subprocess.run")
def test_assemble_video_uses_color_background_when_image_missing(mock_run, tmp_path):
    assemble_video(["문장1"], ["a1.mp3"], [None], str(tmp_path / "out.mp4"))

    first_call_cmd = mock_run.call_args_list[0].args[0]
    assert "lavfi" in first_call_cmd
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd shortsbot && python -m pytest tests/test_video_assembler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_assembler'`

- [ ] **Step 3: 구현**

`shortsbot/video_assembler.py`:
```python
import os
import subprocess


def _escape_drawtext(text: str) -> str:
    """ffmpeg drawtext 필터용 특수문자 이스케이프."""
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _build_segment(image_path: str | None, audio_path: str, text: str, out_path: str) -> None:
    drawtext = (
        f"drawtext=text='{_escape_drawtext(text)}':fontcolor=white:fontsize=48:"
        "box=1:boxcolor=black@0.6:boxborderw=16:x=(w-text_w)/2:y=h-200"
    )
    if image_path is None:
        video_input = ["-f", "lavfi", "-i", "color=c=0x1a1a2e:s=1080x1920"]
    else:
        video_input = ["-loop", "1", "-i", image_path]

    cmd = [
        "ffmpeg", "-y",
        *video_input,
        "-i", audio_path,
        "-vf",
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{drawtext}",
        "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
        "-pix_fmt", "yuv420p", "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def assemble_video(
    sentences: list[str],
    audio_paths: list[str],
    image_paths: list[str | None],
    out_path: str,
) -> str:
    """문장별 세그먼트(이미지/단색배경 + 오디오 + 자막)를 만들어 이어 붙인다."""
    if not (len(sentences) == len(audio_paths) == len(image_paths)):
        raise ValueError(
            "문장/오디오/이미지 개수가 일치하지 않음: "
            f"{len(sentences)}/{len(audio_paths)}/{len(image_paths)}"
        )

    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    segment_paths = []
    for i, (sentence, audio_path, image_path) in enumerate(
        zip(sentences, audio_paths, image_paths), start=1
    ):
        segment_path = os.path.join(out_dir, f"segment_{i}.mp4")
        _build_segment(image_path, audio_path, sentence, segment_path)
        segment_paths.append(segment_path)

    concat_list_path = os.path.join(out_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for segment_path in segment_paths:
            f.write(f"file '{os.path.abspath(segment_path)}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path, "-c", "copy", out_path,
        ],
        check=True,
        capture_output=True,
    )
    return out_path
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd shortsbot && python -m pytest tests/test_video_assembler.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add shortsbot/video_assembler.py shortsbot/tests/test_video_assembler.py
git commit -m "feat(shortsbot): add ffmpeg-based vertical video assembler"
```

---

## Task 6: `description_builder.py` — 설명란 텍스트 조립

**Files:**
- Create: `shortsbot/description_builder.py`
- Test: `shortsbot/tests/test_description_builder.py`

**Interfaces:**
- Produces: `build_description(script_summary: str, products: list[dict], telegram_url: str, keywords: list[str]) -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

`shortsbot/tests/test_description_builder.py`:
```python
from description_builder import build_description


def test_build_description_includes_products_and_telegram_link():
    result = build_description(
        "오늘의 AI 소식 요약",
        [{"productName": "노트북 A", "productUrl": "http://x"}],
        "https://t.me/channel",
        ["노트북"],
    )

    assert "노트북 A: http://x" in result
    assert "https://t.me/channel" in result
    assert "#AI" in result
    assert "#노트북" in result


def test_build_description_omits_product_section_when_empty():
    result = build_description("오늘의 AI 소식 요약", [], "https://t.me/channel", [])

    assert "관련 상품" not in result
    assert "https://t.me/channel" in result
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd shortsbot && python -m pytest tests/test_description_builder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'description_builder'`

- [ ] **Step 3: 구현**

`shortsbot/description_builder.py`:
```python
def build_description(
    script_summary: str, products: list[dict], telegram_url: str, keywords: list[str]
) -> str:
    """쇼츠 설명란 텍스트를 조립한다. 관련상품이 없으면 그 섹션은 생략한다."""
    lines = [script_summary, ""]

    if products:
        lines.append("🔗 관련 상품")
        for p in products:
            lines.append(f"{p['productName']}: {p['productUrl']}")
        lines.append("")

    lines.append(f"📢 AI 뉴스 텔레그램: {telegram_url}")

    if keywords:
        lines.append("")
        hashtags = " ".join(f"#{k.replace(' ', '')}" for k in ["AI", "쇼츠", *keywords])
        lines.append(hashtags)

    return "\n".join(lines)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd shortsbot && python -m pytest tests/test_description_builder.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add shortsbot/description_builder.py shortsbot/tests/test_description_builder.py
git commit -m "feat(shortsbot): add video description builder"
```

---

## Task 7: `youtube_api.py` — 토큰 갱신 + 업로드

**Files:**
- Create: `shortsbot/youtube_api.py`
- Test: `shortsbot/tests/test_youtube_api.py`

**Interfaces:**
- Consumes: `config.Settings`
- Produces: `refresh_access_token(settings: Settings) -> str`, `upload_video(settings: Settings, access_token: str, video_path: str, title: str, description: str) -> str` (반환값은 `https://youtu.be/{video_id}` 형태)

- [ ] **Step 1: 실패하는 테스트 작성**

`shortsbot/tests/test_youtube_api.py`:
```python
from unittest.mock import MagicMock, patch

from config import Settings
from youtube_api import refresh_access_token, upload_video


def _settings():
    return Settings("ak", "gcid", "gcs", "yrt", "chan123", "https://t.me/x")


@patch("youtube_api.requests.post")
def test_refresh_access_token_returns_token(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"access_token": "new-token"}
    mock_post.return_value = mock_response

    token = refresh_access_token(_settings())

    assert token == "new-token"


@patch("youtube_api.MediaFileUpload")
@patch("youtube_api.build")
@patch("youtube_api.Credentials")
def test_upload_video_returns_watch_url_and_sets_public(
    mock_credentials, mock_build, mock_media
):
    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = [(None, {"id": "abc123"})]
    mock_youtube = MagicMock()
    mock_youtube.videos.return_value.insert.return_value = mock_request
    mock_build.return_value = mock_youtube

    url = upload_video(_settings(), "token", "video.mp4", "제목", "설명")

    assert url == "https://youtu.be/abc123"
    insert_kwargs = mock_youtube.videos.return_value.insert.call_args.kwargs
    assert insert_kwargs["body"]["status"]["privacyStatus"] == "public"
    assert insert_kwargs["body"]["snippet"]["channelId"] == "chan123"
    assert insert_kwargs["body"]["snippet"]["title"] == "제목"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd shortsbot && python -m pytest tests/test_youtube_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'youtube_api'`

- [ ] **Step 3: 구현**

`shortsbot/youtube_api.py`:
```python
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import Settings

TOKEN_URL = "https://oauth2.googleapis.com/token"


def refresh_access_token(settings: Settings) -> str:
    """refresh_token으로 새 access_token을 발급받는다."""
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": settings.youtube_refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def upload_video(
    settings: Settings, access_token: str, video_path: str, title: str, description: str
) -> str:
    """영상을 채널에 공개(public)로 업로드하고 시청 URL을 반환한다."""
    credentials = Credentials(token=access_token)
    youtube = build("youtube", "v3", credentials=credentials)
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "channelId": settings.youtube_channel_id,
            },
            "status": {"privacyStatus": "public"},
        },
        media_body=media,
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    return f"https://youtu.be/{response['id']}"
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd shortsbot && python -m pytest tests/test_youtube_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add shortsbot/youtube_api.py shortsbot/tests/test_youtube_api.py
git commit -m "feat(shortsbot): add YouTube Data API upload"
```

---

## Task 8: `main.py` — 오케스트레이션

**Files:**
- Create: `shortsbot/main.py`
- Test: `shortsbot/tests/test_main.py`

**Interfaces:**
- Consumes: Task 1~7의 모든 함수(`load_settings`, `fetch_feed_entries`, `generate_image`, `save_generated_image`, `hash_link`, `load_posted_ids`, `save_posted_ids`, `search_products`, `pick_and_write_script`, `synthesize`, `assemble_video`, `build_description`, `refresh_access_token`, `upload_video`)
- Produces: `run() -> str | None`, `_pick_candidates(entries: list[dict], posted_ids: set[str], limit: int) -> list[dict]` (private)

- [ ] **Step 1: 실패하는 테스트 작성**

`shortsbot/tests/test_main.py`:
```python
from unittest.mock import MagicMock, mock_open, patch

import pytest

import main


def _feed_entries():
    return [
        {
            "title": "t1", "summary": "s1", "link": "http://a",
            "published": (2026, 9, 20, 0, 0, 0, 0, 0, 0),
        },
        {
            "title": "t2", "summary": "s2", "link": "http://b",
            "published": (2026, 9, 22, 0, 0, 0, 0, 0, 0),
        },
        {
            "title": "t3", "summary": "s3", "link": "http://c",
            "published": (2026, 9, 21, 0, 0, 0, 0, 0, 0),
        },
    ]


def test_pick_candidates_returns_unposted_sorted_by_recency_limited():
    entries = _feed_entries()
    posted = {main.hash_link("http://a")}

    result = main._pick_candidates(entries, posted, limit=2)

    assert [e["link"] for e in result] == ["http://b", "http://c"]


@patch("main.save_posted_ids")
@patch("main.upload_video")
@patch("main.refresh_access_token")
@patch("main.build_description")
@patch("main.search_products")
@patch("main.assemble_video")
@patch("main.synthesize")
@patch("main.save_generated_image")
@patch("main.generate_image")
@patch("main.pick_and_write_script")
@patch("main.load_posted_ids")
@patch("main.fetch_feed_entries")
@patch("main.load_settings")
@patch("builtins.open", new_callable=mock_open, read_data="http://feed1\n")
def test_run_uploads_video_for_chosen_candidate(
    mock_file,
    mock_load_settings,
    mock_fetch,
    mock_load_posted,
    mock_pick_script,
    mock_generate_image,
    mock_save_image,
    mock_synth,
    mock_assemble,
    mock_search,
    mock_build_description,
    mock_refresh,
    mock_upload,
    mock_save_posted,
):
    settings = MagicMock()
    settings.telegram_channel_url = "https://t.me/x"
    mock_load_settings.return_value = settings
    mock_fetch.return_value = _feed_entries()
    mock_load_posted.return_value = set()
    mock_pick_script.return_value = {
        "chosen_link": "http://b",
        "title": "제목",
        "sentences": ["문장1", "문장2"],
        "keywords": ["노트북"],
    }
    mock_generate_image.side_effect = [b"bytes1", None]
    mock_save_image.return_value = "work/image_1.png"
    mock_synth.return_value = ["work/1.mp3", "work/2.mp3"]
    mock_assemble.return_value = "work/final.mp4"
    mock_search.return_value = []
    mock_build_description.return_value = "설명"
    mock_refresh.return_value = "token"
    mock_upload.return_value = "https://youtu.be/abc123"

    result = main.run()

    assert result == "https://youtu.be/abc123"
    mock_save_posted.assert_called_once()
    mock_search.assert_called_once_with("노트북")
    mock_assemble.assert_called_once()
    assemble_args = mock_assemble.call_args[0]
    assert assemble_args[0] == ["문장1", "문장2"]
    assert assemble_args[1] == ["work/1.mp3", "work/2.mp3"]
    assert assemble_args[2] == ["work/image_1.png", None]
    mock_build_description.assert_called_once_with(
        "문장1 문장2", [], "https://t.me/x", ["노트북"]
    )
    mock_upload.assert_called_once_with(settings, "token", "work/final.mp4", "제목", "설명")


@patch("main.load_posted_ids")
@patch("main.fetch_feed_entries")
@patch("main.load_settings")
@patch("builtins.open", new_callable=mock_open, read_data="http://feed1\n")
def test_run_returns_none_when_no_entries(
    mock_file, mock_load_settings, mock_fetch, mock_load_posted
):
    mock_load_settings.return_value = object()
    mock_fetch.return_value = []
    mock_load_posted.return_value = set()

    result = main.run()

    assert result is None


@patch("main.load_posted_ids")
@patch("main.fetch_feed_entries")
@patch("main.load_settings")
@patch("builtins.open", new_callable=mock_open, read_data="http://feed1\n")
def test_run_returns_none_when_all_entries_already_posted(
    mock_file, mock_load_settings, mock_fetch, mock_load_posted
):
    entries = _feed_entries()
    mock_load_settings.return_value = object()
    mock_fetch.return_value = entries
    mock_load_posted.return_value = {main.hash_link(e["link"]) for e in entries}

    result = main.run()

    assert result is None


@patch("main.upload_video")
@patch("main.save_posted_ids")
@patch("main.refresh_access_token")
@patch("main.build_description")
@patch("main.search_products")
@patch("main.assemble_video")
@patch("main.synthesize")
@patch("main.save_generated_image")
@patch("main.generate_image")
@patch("main.pick_and_write_script")
@patch("main.load_posted_ids")
@patch("main.fetch_feed_entries")
@patch("main.load_settings")
@patch("builtins.open", new_callable=mock_open, read_data="http://feed1\n")
def test_run_does_not_save_posted_ids_when_upload_fails(
    mock_file,
    mock_load_settings,
    mock_fetch,
    mock_load_posted,
    mock_pick_script,
    mock_generate_image,
    mock_save_image,
    mock_synth,
    mock_assemble,
    mock_search,
    mock_build_description,
    mock_refresh,
    mock_save_posted,
    mock_upload,
):
    settings = MagicMock()
    settings.telegram_channel_url = "https://t.me/x"
    mock_load_settings.return_value = settings
    mock_fetch.return_value = _feed_entries()
    mock_load_posted.return_value = set()
    mock_pick_script.return_value = {
        "chosen_link": "http://b", "title": "제목", "sentences": ["문장1"], "keywords": [],
    }
    mock_generate_image.return_value = b"bytes1"
    mock_save_image.return_value = "work/image_1.png"
    mock_synth.return_value = ["work/1.mp3"]
    mock_assemble.return_value = "work/final.mp4"
    mock_build_description.return_value = "설명"
    mock_refresh.return_value = "token"
    mock_upload.side_effect = RuntimeError("quota exceeded")

    with pytest.raises(RuntimeError):
        main.run()

    mock_save_posted.assert_not_called()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd shortsbot && python -m pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: 구현**

`shortsbot/main.py`:
```python
import datetime
import os

from blogbot_bridge import (
    fetch_feed_entries,
    generate_image,
    hash_link,
    load_posted_ids,
    save_generated_image,
    save_posted_ids,
    search_products,
)
from config import load_settings
from description_builder import build_description
from script_writer import pick_and_write_script
from tts import synthesize
from video_assembler import assemble_video
from youtube_api import refresh_access_token, upload_video

FEEDS_PATH = os.path.join(os.path.dirname(__file__), "..", "blogbot", "feeds.txt")
POSTED_IDS_PATH = "shorts_posted_ids.json"
WORK_DIR = "work"
CANDIDATE_LIMIT = 10


def _load_feed_urls(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _pick_candidates(entries: list[dict], posted_ids: set[str], limit: int) -> list[dict]:
    """미게시 항목을 최신순으로 최대 limit개 반환한다."""
    unposted = [e for e in entries if hash_link(e["link"]) not in posted_ids]
    unposted.sort(key=lambda e: e["published"], reverse=True)
    return unposted[:limit]


def run() -> str | None:
    """숏츠봇 1회 실행. 업로드에 성공하면 영상 URL, 아니면 None."""
    settings = load_settings()

    feed_urls = _load_feed_urls(FEEDS_PATH)
    entries = fetch_feed_entries(feed_urls)
    if not entries:
        print(f"수집된 기사가 없습니다 (피드 {len(feed_urls)}개 모두 실패했을 수 있음).")
        return None

    posted_ids = load_posted_ids(POSTED_IDS_PATH)
    candidates = _pick_candidates(entries, posted_ids, CANDIDATE_LIMIT)
    if not candidates:
        print(f"기사 {len(entries)}건을 수집했지만 새로운 후보가 없습니다.")
        return None

    script = pick_and_write_script(settings, candidates)
    link_hash = hash_link(script["chosen_link"])

    today = datetime.date.today().isoformat()
    work_dir = os.path.join(WORK_DIR, f"{today}-{link_hash[:10]}")
    os.makedirs(work_dir, exist_ok=True)

    image_paths = []
    for i, sentence in enumerate(script["sentences"], start=1):
        image_bytes = generate_image(settings, sentence)
        if image_bytes is None:
            image_paths.append(None)
            continue
        image_paths.append(save_generated_image(work_dir, f"image_{i}.png", image_bytes))

    audio_paths = synthesize(script["sentences"], work_dir)

    video_path = assemble_video(
        script["sentences"], audio_paths, image_paths, os.path.join(work_dir, "final.mp4")
    )

    summary = " ".join(script["sentences"][:2])
    keywords = script.get("keywords", [])
    products = search_products(keywords[0]) if keywords else []
    description = build_description(summary, products, settings.telegram_channel_url, keywords)

    access_token = refresh_access_token(settings)
    video_url = upload_video(settings, access_token, video_path, script["title"], description)

    posted_ids.add(link_hash)
    save_posted_ids(POSTED_IDS_PATH, posted_ids)

    return video_url


if __name__ == "__main__":
    result = run()
    if result:
        print(f"업로드 완료: {result}")
    else:
        print("새로 업로드할 기사가 없습니다.")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd shortsbot && python -m pytest tests/test_main.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 전체 테스트 스위트 확인**

Run: `cd shortsbot && python -m pytest -v`
Expected: 모든 테스트 PASS (Task 1~8 합산)

- [ ] **Step 6: 커밋**

```bash
git add shortsbot/main.py shortsbot/tests/test_main.py
git commit -m "feat(shortsbot): wire up end-to-end orchestration"
```

---

## Task 9: GitHub Actions 워크플로 + README

**Files:**
- Create: `.github/workflows/shortsbot.yml`
- Create: `shortsbot/README.md`

**Interfaces:**
- Consumes: Task 1의 `requirements.txt`, Task 8의 `main.py`

- [ ] **Step 1: 워크플로 작성**

`.github/workflows/shortsbot.yml`:
```yaml
name: ai-shortsbot

on:
  schedule:
    - cron: "0 11 * * *"  # 매일 UTC 11:00 (KST 20:00) — blogbot(KST 09:00)과 겹치지 않게
  workflow_dispatch: {}

permissions:
  contents: write

jobs:
  run-bot:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: shortsbot
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
          YOUTUBE_REFRESH_TOKEN: ${{ secrets.YOUTUBE_REFRESH_TOKEN }}
          YOUTUBE_CHANNEL_ID: ${{ secrets.YOUTUBE_CHANNEL_ID }}
          TELEGRAM_CHANNEL_URL: ${{ secrets.TELEGRAM_CHANNEL_URL }}
          HF_API_KEY: ${{ secrets.HF_API_KEY }}
        run: python main.py
      - name: shorts_posted_ids.json 커밋 (중복게시 이력 유지)
        run: |
          git config user.name "ai-shortsbot"
          git config user.email "ai-shortsbot@users.noreply.github.com"
          git add shorts_posted_ids.json
          git diff --staged --quiet || git commit -m "chore: update shorts_posted_ids"
          git pull --rebase origin master
          git push
```

- [ ] **Step 2: README 작성**

`shortsbot/README.md`:
```markdown
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
- ffmpeg는 GitHub Actions `ubuntu-latest`에 기본 설치되어 있어 별도 설치 불필요. 로컬 실행 시에는 직접 설치
  필요합니다.

## 테스트

`cd shortsbot && python -m pytest -v`
```

- [ ] **Step 3: 커밋**

```bash
git add .github/workflows/shortsbot.yml shortsbot/README.md
git commit -m "feat(shortsbot): add scheduled workflow and README"
```
