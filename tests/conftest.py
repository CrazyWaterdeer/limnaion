"""Shared test fixtures."""
import platformdirs
import pytest


@pytest.fixture(autouse=True)
def _isolate_config_dir(tmp_path, monkeypatch):
    """No test may ever read or write the real user config dir. Redirect
    platformdirs to a per-test tmp dir while keeping 'limnaion' in the path so
    settings_path() still resolves to <tmp>/limnaion/settings.toml."""
    monkeypatch.setattr(
        platformdirs, "user_config_dir", lambda *a, **k: str(tmp_path / "limnaion")
    )


@pytest.fixture(autouse=True)
def _offline_openrouter(monkeypatch):
    """No test may ever fetch the live OpenRouter catalog. Prime the module
    cache to the curated fallback so settings.models_for('openrouter') is
    deterministic and offline. Tests that exercise fetching reset the cache
    (and/or stub fetch_models) themselves."""
    from app import openrouter_models, settings
    monkeypatch.setattr(openrouter_models, "_cache", list(settings.OPENROUTER_MODELS))
