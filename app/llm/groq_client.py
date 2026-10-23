"""Small Groq chat-completions client using Groq's OpenAI-compatible API."""

import os
from typing import Protocol

import requests

from app.settings import Settings, load_settings


class ChatClient(Protocol):
    """Interface used by agents and replaceable by test doubles."""

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, object] | None = None,
    ) -> str:
        """Return the model's text response."""


class GroqConfigurationError(RuntimeError):
    """Raised when the Groq provider is selected but is not configured."""


class GroqProviderError(RuntimeError):
    """Raised when Groq cannot complete a chat request."""


class GroqResponseError(RuntimeError):
    """Raised when Groq returns an unusable chat response."""


class GroqChatClient:
    """Make chat-completion requests to the configured Groq model."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, object] | None = None,
    ) -> str:
        api_key = os.getenv(self.settings.api_key_env)
        if not api_key:
            raise GroqConfigurationError(
                f"Set {self.settings.api_key_env} in the environment to use Groq."
            )

        payload: dict[str, object] = {
            "model": self.settings.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "interview_coach_response",
                    "strict": True,
                    "schema": json_schema,
                },
            }

        try:
            response = requests.post(
                f"{self.settings.api_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code is not None:
                raise GroqProviderError(
                    f"Groq request failed with HTTP {status_code}; check the model, "
                    "account, and usage limits."
                ) from exc
            raise GroqProviderError("Could not connect to the Groq API.") from exc

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise GroqResponseError(
                "Groq returned a response without a chat message."
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise GroqResponseError("Groq returned an empty chat message.")
        return content.strip()
