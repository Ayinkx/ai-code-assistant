"""LLM provider service layer.

Provides a small, provider-agnostic interface for calling a chat-completions
style LLM API. A mock provider is included so development and the test suite
can run without network access or API keys.
"""

from __future__ import annotations

import os
import time
from typing import Protocol

import requests

from app.config import Config

# How long to wait for a single response chunk from the provider (seconds).
TIMEOUT_SECONDS = 60


class LLMProviderError(RuntimeError):
    """Raised when the configured LLM provider cannot fulfil a request."""


def _role(message: MessageType) -> str:
    """Read ``role`` from a message dict or object."""
    return message["role"] if isinstance(message, dict) else message.role


def _content(message: MessageType) -> str:
    """Read ``content`` from a message dict or object."""
    return message["content"] if isinstance(message, dict) else message.content


class MessageType(Protocol):
    """A chat message as consumed by the provider (dict-like)."""

    role: str
    content: str


class LLMProvider(Protocol):
    """Interface implemented by concrete provider clients."""

    def complete(self, messages: list[MessageType], *, stream: bool = False) -> str:
        """Return a complete assistant response for ``messages``."""
        ...

    def stream(self, messages: list[MessageType]):
        """Yield partial assistant responses (strings) for ``messages``."""
        ...


class OpenAIProvider:
    """Client for OpenAI-compatible ``/chat/completions`` endpoints.

    Reads ``OPENAI_API_KEY`` and ``OPENAI_BASE_URL`` from the environment so the
    same client can target OpenAI, a compatible local server (e.g. llama.cpp),
    or a self-hosted gateway.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, messages: list[MessageType], *, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": _role(m), "content": _content(m)} for m in messages],
            "temperature": self.temperature,
            "stream": stream,
        }

    def _require_key(self) -> None:
        if not self.api_key:
            raise LLMProviderError(
                "OPENAI_API_KEY is not set. Configure an LLM provider or use the "
                "mock provider for development."
            )

    def complete(self, messages: list[MessageType], *, stream: bool = False) -> str:
        self._require_key()
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=self._payload(messages, stream=False),
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            raise LLMProviderError(f"LLM provider returned {response.status_code}: {response.text}")
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("LLM provider returned an unexpected response shape.") from exc

    def stream(self, messages: list[MessageType]):
        self._require_key()
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=self._payload(messages, stream=True),
            timeout=TIMEOUT_SECONDS,
            stream=True,
        )
        if response.status_code >= 400:
            raise LLMProviderError(f"LLM provider returned {response.status_code}: {response.text}")

        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            payload = line[len("data: ") :].strip()
            if payload == "[DONE]":
                break
            try:
                chunk = requests.json.loads(payload)
                delta = chunk["choices"][0]["delta"].get("content", "")
            except (KeyError, IndexError, TypeError, ValueError):
                delta = ""
            if delta:
                yield delta


class MockProvider:
    """Deterministic offline provider used by tests and local development.

    Echoes a short canned response so the full chat pipeline (models, routes,
    SSE streaming, UI) can be exercised without network access or an API key.
    """

    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay

    def _respond(self, messages: list[MessageType]) -> str:
        last_user = ""
        for message in messages:
            if _role(message) == "user":
                last_user = _content(message)
        prefix = last_user[:80] + ("..." if len(last_user) > 80 else "")
        return (
            "This is a mock assistant response.\n\n"
            f"You said: {prefix}\n\n"
            "In development mode the mock provider echoes your input back. Configure "
            "OPENAI_API_KEY to enable real AI responses."
        )

    def complete(self, messages: list[MessageType], *, stream: bool = False) -> str:
        if self.delay:
            time.sleep(self.delay)
        return self._respond(messages)

    def stream(self, messages: list[MessageType]):
        text = self._respond(messages)
        for word in text.split(" "):
            if self.delay:
                time.sleep(self.delay)
            yield word + " "


def get_provider() -> LLMProvider:
    """Return the provider configured via ``LLM_PROVIDER`` (default ``mock``)."""
    name = os.getenv("LLM_PROVIDER", Config.LLM_PROVIDER).lower()
    if name == "openai":
        return OpenAIProvider()
    return MockProvider()
