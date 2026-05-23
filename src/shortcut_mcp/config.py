"""Configuration for the Shortcut MCP server."""

from __future__ import annotations

import enum

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class ShortcutMode(enum.StrEnum):
    READONLY = "readonly"
    READWRITE = "readwrite"


class ShortcutConfig(BaseSettings):
    """Env-loaded settings. Frozen — no runtime promotion of safety tier."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "frozen": True,
    }

    shortcut_api_token: SecretStr | None = None

    shortcut_mode: ShortcutMode = ShortcutMode.READONLY
    shortcut_allow_destructive: bool = False

    shortcut_api_base_url: str = "https://api.app.shortcut.com/api/v3"
    shortcut_request_timeout: int = Field(default=30, gt=0)
    shortcut_max_retries: int = Field(default=3, ge=1)

    @property
    def authenticated(self) -> bool:
        return self.shortcut_api_token is not None and bool(self.shortcut_api_token.get_secret_value())

    @property
    def writes_enabled(self) -> bool:
        return self.shortcut_mode is ShortcutMode.READWRITE

    @property
    def destructive_enabled(self) -> bool:
        return self.writes_enabled and self.shortcut_allow_destructive
