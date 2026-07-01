"""Phase E packaging guards: dead config gone, LICENSE/README present."""
from pathlib import Path

from app import config, types

ROOT = Path(__file__).resolve().parent.parent


def test_dead_config_removed():
    for name in ("REFEREE_BACKEND", "SCRIBE_BACKEND", "CLAUDE_USE_SUBSCRIPTION",
                 "GEMINI_MODEL", "GEMINI_ENV_PATH", "gemini_api_key", "ROLL_SH"):
        assert not hasattr(config, name), f"dead config still present: {name}"
    assert not hasattr(types, "Backend"), "dead types.Backend still present"


def test_live_config_intact():
    # the real defaults must survive the cleanup
    assert config.NARRATOR.model == config.CLAUDE_OPUS
    assert config.OPENROUTER_BASE_URL.startswith("https://")
    assert callable(config.openrouter_api_key)


def test_license_is_gpl3():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in text
    assert "Version 3" in text


def test_readme_mentions_limnaion_and_install():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "limnaion" in readme
    assert "pipx" in readme or "pip install" in readme
