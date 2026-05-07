"""LM Studio-backed LLM service for chat completions."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_API_KEY = "lm-studio"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_TOKENS = 512

ChatMessage = dict[str, str]


def _get_float_env(name: str, default: float) -> float:
    """Read a float configuration value from the environment."""
    value = os.getenv(name)
    if value in (None, ""):
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid float.") from exc


def _get_int_env(name: str, default: int | None) -> int | None:
    """Read an integer configuration value from the environment."""
    value = os.getenv(name)
    if value in (None, ""):
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid integer.") from exc


class LLMService:
    """Wrap LM Studio's OpenAI-compatible API for chat interactions."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        load_dotenv()

        self.base_url = (base_url or os.getenv("LM_STUDIO_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.model_name = model_name or os.getenv("MODEL_NAME")
        self.api_key = api_key or os.getenv("LM_STUDIO_API_KEY") or DEFAULT_API_KEY
        self.temperature = (
            _get_float_env("LM_STUDIO_TEMPERATURE", DEFAULT_TEMPERATURE)
            if temperature is None
            else temperature
        )
        self.timeout = (
            _get_float_env("LM_STUDIO_TIMEOUT", DEFAULT_TIMEOUT)
            if timeout is None
            else timeout
        )
        self.max_tokens = (
            _get_int_env("LM_STUDIO_MAX_TOKENS", DEFAULT_MAX_TOKENS)
            if max_tokens is None
            else max_tokens
        )

        if not self.model_name:
            raise ValueError(
                "MODEL_NAME is not configured. Set it in .env or pass it to LLMService."
            )

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )

    def list_models(self) -> list[str]:
        """Return model identifiers currently exposed by the LM Studio server."""
        try:
            models = self.client.models.list()
        except OpenAIError as exc:
            raise RuntimeError(
                "Unable to reach the LM Studio models endpoint. Make sure the local server is running."
            ) from exc

        return [model.id for model in models.data]

    def generate_response(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send chat messages to LM Studio and return the assistant's reply text."""
        if not messages:
            raise ValueError("messages cannot be empty.")

        request_payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
        }

        resolved_max_tokens = self.max_tokens if max_tokens is None else max_tokens
        if resolved_max_tokens is not None:
            request_payload["max_tokens"] = resolved_max_tokens

        try:
            completion = self.client.chat.completions.create(**request_payload)
        except OpenAIError as exc:
            raise RuntimeError(
                "Unable to get a response from LM Studio. Make sure the local server is running and a model is loaded."
            ) from exc

        if not completion.choices:
            raise RuntimeError("LM Studio returned no completion choices.")

        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("LM Studio returned an empty response.")

        return content.strip()
