"""Configuration helpers for the Azure Bot Framework bot."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Read configuration values from environment variables with sensible defaults."""

    microsoft_app_id: str = os.getenv("MICROSOFT_APP_ID", "")
    microsoft_app_password: str = os.getenv("MICROSOFT_APP_PASSWORD", "")
    port: int = int(os.getenv("PORT", 3978))

    azure_openai_endpoint: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_key: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
    azure_openai_temperature: float = float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.2"))
    azure_openai_max_tokens: int = int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "800"))

    @property
    def is_openai_configured(self) -> bool:
        """Return ``True`` when enough settings are provided for Azure OpenAI calls."""

        return all(
            [
                self.azure_openai_endpoint,
                self.azure_openai_deployment,
                self.azure_openai_api_key,
            ]
        )
