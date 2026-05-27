"""Configuration for the Shortcut MCP server."""

from __future__ import annotations

import enum

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class ShortcutMode(enum.StrEnum):
    READONLY = "readonly"
    READWRITE = "readwrite"


class ToolProfile(enum.StrEnum):
    CORE = "core"
    PLANNING = "planning"
    FILES = "files"
    ALL = "all"


ALL_MODULES: frozenset[str] = frozenset(
    {
        "story",
        "story_comment",
        "story_task",
        "story_link",
        "epic",
        "epic_comment",
        "epic_workflow",
        "iteration",
        "objective",
        "member",
        "group",
        "workflow",
        "label",
        "project",
        "file",
        "linked_file",
        "repository",
        "external_link",
        "key_result",
        "custom_field",
        "category",
        "entity_template",
        "document",
        "health",
        "feature_toggle",
        "search",
    }
)

_CORE_MODULES: frozenset[str] = frozenset(
    {
        "story",
        "story_comment",
        "story_task",
        "story_link",
        "epic",
        "epic_comment",
        "epic_workflow",
        "iteration",
        "objective",
        "member",
        "workflow",
        "label",
        "search",
    }
)

PROFILE_MODULES: dict[ToolProfile, frozenset[str]] = {
    ToolProfile.CORE: _CORE_MODULES,
    ToolProfile.PLANNING: _CORE_MODULES | {"group", "project"},
    ToolProfile.FILES: _CORE_MODULES | {"file", "linked_file"},
    ToolProfile.ALL: ALL_MODULES,
}


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

    shortcut_profile: ToolProfile = ToolProfile.CORE
    shortcut_tools: str = ""

    @field_validator("shortcut_tools")
    @classmethod
    def _validate_tools(cls, raw: str) -> str:
        names = {n.strip() for n in raw.split(",") if n.strip()}
        unknown = names - ALL_MODULES
        if unknown:
            raise ValueError(f"unknown SHORTCUT_TOOLS module(s): {sorted(unknown)}")
        return raw

    @property
    def authenticated(self) -> bool:
        return self.shortcut_api_token is not None and bool(self.shortcut_api_token.get_secret_value())

    @property
    def writes_enabled(self) -> bool:
        return self.shortcut_mode is ShortcutMode.READWRITE

    @property
    def destructive_enabled(self) -> bool:
        return self.writes_enabled and self.shortcut_allow_destructive

    @property
    def enabled_modules(self) -> frozenset[str]:
        names = frozenset(n.strip() for n in self.shortcut_tools.split(",") if n.strip())
        return names if names else PROFILE_MODULES[self.shortcut_profile]
