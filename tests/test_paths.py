"""E2 — verify that package data paths land inside app/data/ and that
GAMES_DIR resolution follows the correct three-level precedence."""

from __future__ import annotations

import os
from pathlib import Path

import platformdirs
import pytest

import app.config as config
from app.game_files import GAME_FILE_NAMES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _expected_data_dir() -> Path:
    """The app/data/ directory derived from config.__file__ (no globals assumed)."""
    return Path(config.__file__).resolve().parent / "data"


# ---------------------------------------------------------------------------
# ENGINE_MD / TEMPLATES_DIR must be inside app/data/
# ---------------------------------------------------------------------------

def test_engine_md_is_under_app_data() -> None:
    expected = _expected_data_dir() / "engine.md"
    assert config.ENGINE_MD == expected, (
        f"ENGINE_MD should be {expected}, got {config.ENGINE_MD}"
    )
    assert config.ENGINE_MD.is_file(), f"ENGINE_MD does not exist: {config.ENGINE_MD}"


def test_templates_dir_is_under_app_data() -> None:
    expected = _expected_data_dir() / "templates"
    assert config.TEMPLATES_DIR == expected, (
        f"TEMPLATES_DIR should be {expected}, got {config.TEMPLATES_DIR}"
    )
    assert config.TEMPLATES_DIR.is_dir(), (
        f"TEMPLATES_DIR is not a directory: {config.TEMPLATES_DIR}"
    )


def test_templates_dir_contains_all_five_templates() -> None:
    """game_files.new_game_from_templates depends on finding all five files here."""
    expected = _expected_data_dir() / "templates"
    assert config.TEMPLATES_DIR == expected, (
        f"TEMPLATES_DIR should be under app/data, got {config.TEMPLATES_DIR}"
    )
    missing = [n for n in GAME_FILE_NAMES if not (config.TEMPLATES_DIR / n).is_file()]
    assert missing == [], f"Missing template files: {missing}"


# ---------------------------------------------------------------------------
# GAMES_DIR three-level resolution (via the private helper)
# ---------------------------------------------------------------------------

def test_games_dir_env_override_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """LIMNAION_GAMES_DIR env var beats everything else."""
    target = tmp_path / "custom_games"
    monkeypatch.setenv("LIMNAION_GAMES_DIR", str(target))
    result = config._resolve_games_dir()
    assert result == target


def test_games_dir_dev_checkout_wins_over_user_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no env var is set and a games/ subdir exists alongside a repo marker, use it."""
    monkeypatch.delenv("LIMNAION_GAMES_DIR", raising=False)
    fake_root = tmp_path / "repo"
    (fake_root / "games").mkdir(parents=True)
    # Provide a repo marker (pyproject.toml) so the hardened check passes.
    (fake_root / "pyproject.toml").write_text("[project]\nname = \"fake\"\n", encoding="utf-8")
    result = config._resolve_games_dir(_root=fake_root)
    assert result == fake_root / "games"


def test_games_dir_falls_back_to_user_data_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no env var and no games/ in the root, fall back to platformdirs."""
    monkeypatch.delenv("LIMNAION_GAMES_DIR", raising=False)
    # fake_root exists but has no games/ subdir
    fake_root = tmp_path / "repo_no_games"
    fake_root.mkdir()
    user_data_base = tmp_path / "userdata"
    monkeypatch.setattr(
        platformdirs, "user_data_dir", lambda *a, **k: str(user_data_base)
    )
    result = config._resolve_games_dir(_root=fake_root)
    assert result == user_data_base / "games"
