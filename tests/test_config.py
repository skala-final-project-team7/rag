"""app.config.Settings — 환경 설정 로딩 검증."""

import pytest

from app.config import Settings, get_settings


def test_settings_instantiates_with_defaults() -> None:
    # 환경 변수 없이도 기본값으로 생성 가능해야 한다 (로컬 개발 편의)
    settings = Settings()
    assert settings.source_type == "json_fixture"
    assert settings.qdrant_port == 6333
    assert settings.llm_answer_model == "gpt-4o"
    assert settings.llm_aux_model == "gpt-4o-mini"
    assert settings.openai_api_key.get_secret_value() == ""


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_QDRANT_PORT", "9999")
    monkeypatch.setenv("RAG_SOURCE_TYPE", "atlassian")
    settings = Settings()
    assert settings.qdrant_port == 9999
    assert settings.source_type == "atlassian"


def test_openai_api_key_is_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_OPENAI_API_KEY", "sk-secret-value")
    settings = Settings()
    # 평문 시크릿이 repr/str에 노출되지 않아야 한다
    assert "sk-secret-value" not in repr(settings)
    assert "sk-secret-value" not in str(settings)
    assert settings.openai_api_key.get_secret_value() == "sk-secret-value"


def test_get_settings_returns_settings() -> None:
    assert isinstance(get_settings(), Settings)
