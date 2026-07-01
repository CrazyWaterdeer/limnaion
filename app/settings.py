"""User settings: load/save settings.toml and resolve role/UX configuration.

A thin layer over config.py defaults. Read with tomllib (stdlib), written with
tomli_w, stored under the platformdirs user config dir. A partial or missing file
falls back to the built-in defaults field by field. No Textual imports — pure.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import platformdirs
import tomli_w

from app import config
from app.types import RoleConfig

APP_NAME = "limnaion"

NARRATION_LENGTHS = ("short", "medium", "long")
FROG_TONES = ("bookends", "always", "off")
PROVIDERS = ("claude-subscription", "openrouter")
# Curated subset of Textual's built-in themes (all verified present in 8.2.7).
AVAILABLE_THEMES = (
    "textual-dark", "gruvbox", "dracula", "monokai",
    "catppuccin-mocha", "catppuccin-latte", "flexoki", "ansi-dark",
)

DEFAULT_NARRATION_LENGTH = "medium"
DEFAULT_THEME = "gruvbox"
DEFAULT_FROG_TONE = "bookends"

# (label, value) options per provider for the settings dropdowns.
CLAUDE_MODELS = [
    ("Opus 4.8", config.CLAUDE_OPUS),
    ("Sonnet 5", config.CLAUDE_SONNET),
    ("Haiku 4.5", config.CLAUDE_HAIKU),
]
# Curated current OpenRouter slugs (validated against the live /api/v1/models on
# 2026-07-01). The catalog moves fast; settings.toml accepts any slug, and the
# load_settings path keeps a saved model even if it is not in this list.
OPENROUTER_MODELS = [
    ("Gemini 3.5 Flash", "google/gemini-3.5-flash"),
    ("Gemini 3.1 Flash Lite", "google/gemini-3.1-flash-lite"),
    ("GPT-5.5", "openai/gpt-5.5"),
    ("GPT-5.4", "openai/gpt-5.4"),
    ("Claude Sonnet 4.6", "anthropic/claude-sonnet-4.6"),
    ("DeepSeek V4", "deepseek/deepseek-v4-flash"),
    ("Kimi K2.6", "moonshotai/kimi-k2.6"),
    ("Llama 4 Maverick", "meta-llama/llama-4-maverick"),
]


def models_for(provider: str) -> list[tuple[str, str]]:
    """Model (label, value) options for a provider's dropdown. Claude is a fixed
    trio; OpenRouter uses the live catalog (cached, with a curated fallback)."""
    if provider == "claude-subscription":
        return list(CLAUDE_MODELS)
    from app import openrouter_models  # lazy: break the settings <-> models cycle
    return openrouter_models.live_openrouter_models()


def model_options(provider: str, current: str) -> list[tuple[str, str]]:
    """Options for a model Select, guaranteeing `current` is selectable
    (a model loaded from settings.toml might not be in the curated list)."""
    opts = models_for(provider)
    if current not in [v for _, v in opts]:
        opts = [(current, current), *opts]
    return opts


@dataclass
class Settings:
    narrator: RoleConfig
    referee: RoleConfig
    scribe: RoleConfig
    narration_length: str = DEFAULT_NARRATION_LENGTH
    theme: str = DEFAULT_THEME
    frog_tone: str = DEFAULT_FROG_TONE
    openrouter_api_key: str = ""


def default_settings() -> Settings:
    return Settings(
        narrator=config.NARRATOR,
        referee=config.REFEREE,
        scribe=config.SCRIBE,
        narration_length=DEFAULT_NARRATION_LENGTH,
        theme=DEFAULT_THEME,
        frog_tone=DEFAULT_FROG_TONE,
        openrouter_api_key="",
    )


def settings_path() -> Path:
    return Path(platformdirs.user_config_dir(APP_NAME)) / "settings.toml"


def _role_from(data: dict, default: RoleConfig) -> RoleConfig:
    if not isinstance(data, dict):
        return default
    provider = data.get("provider", default.provider)
    if provider not in PROVIDERS:
        provider = default.provider
    model = data.get("model", default.model)
    if not isinstance(model, str) or not model:
        model = default.model
    return RoleConfig(provider, model)


def _choice(value: object, allowed: tuple, default: object) -> object:
    return value if value in allowed else default


def from_toml_dict(data: dict) -> Settings:
    d = default_settings()
    providers = data.get("providers", {})
    if not isinstance(providers, dict):
        providers = {}
    return Settings(
        narrator=_role_from(providers.get("narrator", {}), d.narrator),
        referee=_role_from(providers.get("referee", {}), d.referee),
        scribe=_role_from(providers.get("scribe", {}), d.scribe),
        narration_length=_choice(data.get("narration_length"), NARRATION_LENGTHS, d.narration_length),
        theme=_choice(data.get("theme"), AVAILABLE_THEMES, d.theme),
        frog_tone=_choice(data.get("frog_tone"), FROG_TONES, d.frog_tone),
        openrouter_api_key=str(data.get("openrouter_api_key", "") or ""),
    )


def to_toml_dict(s: Settings) -> dict:
    return {
        "narration_length": s.narration_length,
        "theme": s.theme,
        "frog_tone": s.frog_tone,
        "openrouter_api_key": s.openrouter_api_key,
        "providers": {
            "narrator": {"provider": s.narrator.provider, "model": s.narrator.model},
            "referee": {"provider": s.referee.provider, "model": s.referee.model},
            "scribe": {"provider": s.scribe.provider, "model": s.scribe.model},
        },
    }


def load_settings(path: Path | None = None) -> Settings:
    path = Path(path or settings_path())
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default_settings()
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return default_settings()
    return from_toml_dict(data)


def save_settings(s: Settings, path: Path | None = None) -> None:
    path = Path(path or settings_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(tomli_w.dumps(to_toml_dict(s)), encoding="utf-8")
    tmp.replace(path)
