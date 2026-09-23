import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    anthropic_api_key: str
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    blogger_blog_id: str
    gemini_api_key: str = ""


def load_settings() -> Settings:
    load_dotenv()
    required = [
        "ANTHROPIC_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
        "BLOGGER_BLOG_ID",
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"필수 환경변수 누락: {', '.join(missing)}")

    return Settings(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        google_client_id=os.environ["GOOGLE_CLIENT_ID"],
        google_client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        google_refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        blogger_blog_id=os.environ["BLOGGER_BLOG_ID"],
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
    )
