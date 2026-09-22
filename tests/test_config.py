import pytest

from config import load_settings


def test_load_settings_raises_when_keys_missing(monkeypatch):
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("COUPANG_ACCESS_KEY", raising=False)
    monkeypatch.delenv("COUPANG_SECRET_KEY", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(RuntimeError, match="필수 환경변수 누락"):
        load_settings()


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("COUPANG_ACCESS_KEY", "ak")
    monkeypatch.setenv("COUPANG_SECRET_KEY", "sk")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tt")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "cid")
    monkeypatch.delenv("MIN_DISCOUNT_RATE", raising=False)

    settings = load_settings()

    assert settings.access_key == "ak"
    assert settings.min_discount_rate == 30
