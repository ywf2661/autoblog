import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    anthropic_api_key: str
    coupang_access_key: str
    coupang_secret_key: str
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    blogger_blog_id: str


def load_settings() -> Settings:
    load_dotenv()
    # 쿠팡파트너스 키는 선택값: 최종승인(누적 판매 15만원) 전에는 발급이 안 되므로,
    # 없으면 coupang_search가 빈 결과로 건너뛰고 나머지 파이프라인은 그대로 동작한다.
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
        coupang_access_key=os.getenv("COUPANG_ACCESS_KEY", ""),
        coupang_secret_key=os.getenv("COUPANG_SECRET_KEY", ""),
        google_client_id=os.environ["GOOGLE_CLIENT_ID"],
        google_client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        google_refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        blogger_blog_id=os.environ["BLOGGER_BLOG_ID"],
    )
