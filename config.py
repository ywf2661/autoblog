import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    access_key: str
    secret_key: str
    telegram_token: str
    telegram_chat_id: str
    min_discount_rate: int = 30


def load_settings() -> Settings:
    load_dotenv()
    required = [
        "COUPANG_ACCESS_KEY",
        "COUPANG_SECRET_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"필수 환경변수 누락: {', '.join(missing)}")

    return Settings(
        access_key=os.environ["COUPANG_ACCESS_KEY"],
        secret_key=os.environ["COUPANG_SECRET_KEY"],
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=os.environ["TELEGRAM_CHAT_ID"],
        min_discount_rate=int(os.getenv("MIN_DISCOUNT_RATE", "30")),
    )
