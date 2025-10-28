"""Azure OpenAI service wrapper for generating conversational replies."""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Optional, Sequence

import aiohttp

from .config import Config

_LOGGER = logging.getLogger(__name__)


class AzureOpenAIService:
    """Call Azure OpenAI chat completions to craft responses."""

    def __init__(self, config: Config, *, timeout_seconds: int = 30) -> None:
        self._config = config
        self._timeout_seconds = timeout_seconds

    @property
    def _endpoint(self) -> Optional[str]:
        endpoint = self._config.azure_openai_endpoint
        if endpoint and not endpoint.rstrip("/").endswith("openai"):  # align with resource URL
            endpoint = endpoint.rstrip("/") + "/openai"
        return endpoint

    def is_configured(self) -> bool:
        """Return ``True`` when Azure OpenAI credentials are set."""

        return self._config.is_openai_configured

    async def generate_reply(self, history: Sequence[dict]) -> Optional[str]:
        """Generate a reply using Azure OpenAI or ``None`` when unavailable."""

        if not self.is_configured():
            return None

        payload = {
            "messages": _truncate_history(history),
            "max_tokens": self._config.azure_openai_max_tokens,
            "temperature": self._config.azure_openai_temperature,
        }
        url = (
            f"{self._endpoint}/deployments/{self._config.azure_openai_deployment}/chat/completions"
            f"?api-version={self._config.azure_openai_api_version}"
        )
        headers = {
            "Content-Type": "application/json",
            "api-key": self._config.azure_openai_api_key or "",
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout_seconds)) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    data = await response.json()
                    if response.status != 200:
                        _LOGGER.error("Azure OpenAI error %s: %s", response.status, data)
                        return None
        except asyncio.TimeoutError:
            _LOGGER.warning("Azure OpenAI request timed out")
            return None
        except aiohttp.ClientError as exc:
            _LOGGER.error("Azure OpenAI HTTP error: %s", exc)
            return None

        choices: Iterable[dict] = data.get("choices", [])  # type: ignore[assignment]
        for choice in choices:
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content.strip()
        return None


def _truncate_history(history: Sequence[dict], *, max_messages: int = 20) -> List[dict]:
    """Limit the conversation history to keep payload sizes manageable."""

    if len(history) <= max_messages:
        return list(history)
    return list(history[-max_messages:])
