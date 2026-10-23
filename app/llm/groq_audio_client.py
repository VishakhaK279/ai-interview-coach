"""Groq audio transcription client."""

import os

import requests

from app.llm.groq_client import (
    GroqConfigurationError,
    GroqProviderError,
    GroqResponseError,
)
from app.settings import Settings, load_settings


class GroqAudioTranscriber:
    """Transcribe an in-memory audio recording through Groq's API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()

    def transcribe(self, audio: bytes, filename: str, content_type: str) -> str:
        api_key = os.getenv(self.settings.api_key_env)
        if not api_key:
            raise GroqConfigurationError(
                f"Set {self.settings.api_key_env} in the environment to use Groq."
            )
        if not audio:
            raise GroqResponseError("The audio recording is empty.")

        try:
            response = requests.post(
                f"{self.settings.api_base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data={"model": "whisper-large-v3-turbo", "response_format": "json"},
                files={"file": (filename, audio, content_type)},
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code is not None:
                raise GroqProviderError(
                    f"Groq transcription failed with HTTP {status_code}; check the "
                    "model, account, and usage limits."
                ) from exc
            raise GroqProviderError("Could not connect to the Groq API.") from exc

        try:
            text = response.json()["text"]
        except (ValueError, KeyError, TypeError) as exc:
            raise GroqResponseError(
                "Groq returned a transcription without text."
            ) from exc
        if not isinstance(text, str) or not text.strip():
            raise GroqResponseError("Groq returned an empty transcription.")
        return text.strip()
