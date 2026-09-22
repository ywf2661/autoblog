import pytest

from config import load_settings


def test_load_settings_raises_when_keys_missing(monkeypatch):
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)
    for key in [
        "ANTHROPIC_API_KEY",
        "COUPANG_ACCESS_KEY",
        "COUPANG_SECRET_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
        "BLOGGER_BLOG_ID",
    ]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError, match="필수 환경변수 누락"):
        load_settings()


def test_load_settings_allows_missing_coupang_keys(monkeypatch):
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ak")
    monkeypatch.delenv("COUPANG_ACCESS_KEY", raising=False)
    monkeypatch.delenv("COUPANG_SECRET_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "gcid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "gcs")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "grt")
    monkeypatch.setenv("BLOGGER_BLOG_ID", "blogid")

    settings = load_settings()

    assert settings.coupang_access_key == ""
    assert settings.coupang_secret_key == ""


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ak")
    monkeypatch.setenv("COUPANG_ACCESS_KEY", "cak")
    monkeypatch.setenv("COUPANG_SECRET_KEY", "csk")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "gcid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "gcs")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "grt")
    monkeypatch.setenv("BLOGGER_BLOG_ID", "blogid")

    settings = load_settings()

    assert settings.anthropic_api_key == "ak"
    assert settings.blogger_blog_id == "blogid"
