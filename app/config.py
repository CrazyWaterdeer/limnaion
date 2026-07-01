from __future__ import annotations

import os
from pathlib import Path

import platformdirs

from app.types import RoleConfig

# ---------------------------------------------------------------------------
# Repo / framework root (unchanged — still the parent of the app/ package)
# ---------------------------------------------------------------------------

FRAMEWORK_ROOT: Path = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Package-data paths — engine.md and templates live INSIDE the app package so
# they ship with pip/pipx installs without any extra data-file configuration
# beyond the hatchling include rule added in Task E4.
# ---------------------------------------------------------------------------

_DATA: Path = Path(__file__).resolve().parent / "data"
ENGINE_MD: Path = _DATA / "engine.md"
TEMPLATES_DIR: Path = _DATA / "templates"

# ---------------------------------------------------------------------------
# Model / provider constants
# ---------------------------------------------------------------------------

CLAUDE_OPUS: str = "claude-opus-4-8"
CLAUDE_SONNET: str = "claude-sonnet-5"    # current flagship Sonnet (2026-06-30)
CLAUDE_HAIKU: str = "claude-haiku-4-5-20251001"
CLAUDE_MODEL: str = CLAUDE_HAIKU          # keep this name; existing refs use it
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

NARRATOR: RoleConfig = RoleConfig("claude-subscription", CLAUDE_OPUS)
REFEREE: RoleConfig = RoleConfig("claude-subscription", CLAUDE_HAIKU)
SCRIBE: RoleConfig = RoleConfig("claude-subscription", CLAUDE_HAIKU)

RECENT_TURNS_K: int = 6
LOG_COMPRESS_THRESHOLD: int = 20
UNDO_SNAPSHOTS: int = 5  # per-game turn snapshots retained for Ctrl+Z undo
MODEL_TIMEOUT: int = 150  # per model call; creator/narration via `claude -p` can take 20-60s+

# ---------------------------------------------------------------------------
# GAMES_DIR — resolved once at import time; tests override via monkeypatch
# ---------------------------------------------------------------------------


def _resolve_games_dir(_root: Path | None = None) -> Path:
    """Resolve the games directory with three-level precedence.

    1. ``LIMNAION_GAMES_DIR`` environment variable (absolute path override).
    2. ``<root>/games/`` if that directory already exists — the dev-checkout case.
    3. ``platformdirs.user_data_dir("limnaion") / "games"`` — installed-package case.

    The optional *_root* parameter substitutes for ``FRAMEWORK_ROOT`` so that
    unit tests can exercise all three branches without touching module globals.
    """
    env = os.environ.get("LIMNAION_GAMES_DIR")
    if env:
        return Path(env)
    root = _root if _root is not None else FRAMEWORK_ROOT
    dev = root / "games"
    if dev.is_dir() and (
        (root / "pyproject.toml").is_file() or (root / ".git").exists()
    ):
        return dev
    return Path(platformdirs.user_data_dir("limnaion")) / "games"


GAMES_DIR: Path = _resolve_games_dir()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def openrouter_api_key() -> str:
    """Return OPENROUTER_API_KEY from the environment (KeyError if unset)."""
    return os.environ["OPENROUTER_API_KEY"]


def game_dir(slug: str) -> Path:
    return GAMES_DIR / slug
