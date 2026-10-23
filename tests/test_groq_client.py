import os

import pytest

from app.llm.groq_client import (
    GroqChatClient,
    GroqConfigurationError,
    GroqResponseError,
)
from app.llm.groq_audio_client import GroqAudioTranscriber
from app.settings import Settings
from app.settings import load_settings


def make_settings() -> Settings:
    return Settings(
        agent_mode="groq",
        api_key_env="GROQ_API_KEY",
        model="test-model",
        api_base_url="https://api.groq.com/openai/v1",
        request_timeout_seconds=10,
    )


def test_settings_load_groq_key_from_env_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GROQ_API_KEY=test-from-env-file\n", encoding="utf-8")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    settings = load_settings(env_file)

    assert settings.api_key_env == "GROQ_API_KEY"
    assert os.environ["GROQ_API_KEY"] == "test-from-env-file"


def test_groq_client_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(GroqConfigurationError, match="GROQ_API_KEY"):
        GroqChatClient(make_settings()).complete("system", "user")


def test_groq_client_sends_chat_request(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "hello"}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("app.llm.groq_client.requests.post", fake_post)

    assert GroqChatClient(make_settings()).complete("system prompt", "user prompt") == "hello"
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "user prompt"},
    ]


def test_groq_client_requests_strict_json_schema(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("app.llm.groq_client.requests.post", fake_post)
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }

    GroqChatClient(make_settings()).complete("system", "user", json_schema=schema)

    assert captured["json"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "interview_coach_response",
            "strict": True,
            "schema": schema,
        },
    }


def test_groq_client_rejects_empty_response(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-secret")

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"choices": [{"message": {"content": " "}}]}

    def fake_post(url, **kwargs):
        assert url.endswith("/chat/completions")
        assert kwargs["timeout"] == 10
        return FakeResponse()

    monkeypatch.setattr("app.llm.groq_client.requests.post", fake_post)

    with pytest.raises(GroqResponseError, match="empty"):
        GroqChatClient(make_settings()).complete("system", "user")


def test_groq_audio_transcriber_sends_recording_and_returns_text(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"text": "I used Python to build a data pipeline."}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("app.llm.groq_audio_client.requests.post", fake_post)

    transcription = GroqAudioTranscriber(make_settings()).transcribe(
        b"audio bytes",
        "answer.webm",
        "audio/webm",
    )

    assert transcription == "I used Python to build a data pipeline."
    assert captured["url"].endswith("/audio/transcriptions")
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert captured["data"] == {
        "model": "whisper-large-v3-turbo",
        "response_format": "json",
    }
    assert captured["files"]["file"] == ("answer.webm", b"audio bytes", "audio/webm")