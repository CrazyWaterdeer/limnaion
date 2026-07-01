"""Tests for app.openrouter_models: live OpenRouter catalog with curated fallback.

No test hits the network — every test injects a fake `fetch` or stubs
`fetch_models`. The autouse conftest fixture primes the module cache to the
curated fallback; tests that exercise fetching reset it explicitly.
"""
import json

from app import openrouter_models, settings

# A representative slice of the OpenRouter /models payload: several preferred
# providers with varying `created` timestamps, one non-preferred provider
# (cohere/) that MUST be filtered out, and one entry with no `name` (so the id
# is used as its label).
SAMPLE = {
    "data": [
        {"id": "google/gemini-3.5-flash", "name": "Gemini 3.5 Flash", "created": 1730000000},
        {"id": "openai/gpt-5.5", "name": "GPT-5.5", "created": 1740000000},
        {"id": "anthropic/claude-sonnet-4.6", "name": "Claude Sonnet 4.6", "created": 1735000000},
        {"id": "deepseek/deepseek-v4-flash", "name": "DeepSeek V4", "created": 1720000000},
        {"id": "cohere/command-r", "name": "Command R", "created": 1750000000},
        {"id": "x-ai/grok-5", "name": "Grok 5", "created": 1745000000},
        {"id": "moonshotai/kimi-k2.6", "created": 1710000000},
    ]
}

# cohere/ dropped (not preferred); remaining sorted by `created` descending;
# the kimi entry has no name, so its id doubles as the label.
EXPECTED = [
    ("Grok 5", "x-ai/grok-5"),
    ("GPT-5.5", "openai/gpt-5.5"),
    ("Claude Sonnet 4.6", "anthropic/claude-sonnet-4.6"),
    ("Gemini 3.5 Flash", "google/gemini-3.5-flash"),
    ("DeepSeek V4", "deepseek/deepseek-v4-flash"),
    ("moonshotai/kimi-k2.6", "moonshotai/kimi-k2.6"),
]


def _fetch_returning(payload, calls=None):
    """Build a fake `fetch(url, timeout)` that returns `payload` as JSON bytes."""
    def _fetch(url, timeout):
        if calls is not None:
            calls["n"] += 1
        assert url == openrouter_models.OPENROUTER_MODELS_URL
        assert timeout == 10
        return json.dumps(payload).encode("utf-8")
    return _fetch


def test_fetch_models_filters_sorts_and_maps():
    result = openrouter_models.fetch_models(fetch=_fetch_returning(SAMPLE))
    assert result == EXPECTED


def test_fetch_models_caps_at_24():
    data = [{"id": f"openai/m{i}", "name": f"M{i}", "created": i} for i in range(30)]
    result = openrouter_models.fetch_models(fetch=_fetch_returning({"data": data}))
    assert len(result) == 24
    assert result[0] == ("M29", "openai/m29")   # newest kept
    assert result[-1] == ("M6", "openai/m6")     # oldest within the cap


def test_fetch_models_passes_custom_timeout():
    captured = {}

    def _fetch(url, timeout):
        captured["timeout"] = timeout
        return json.dumps(SAMPLE).encode("utf-8")

    openrouter_models.fetch_models(fetch=_fetch, timeout=3)
    assert captured["timeout"] == 3


def test_fetch_models_falls_back_on_network_error():
    def _boom(url, timeout):
        raise OSError("network down")

    assert openrouter_models.fetch_models(fetch=_boom) == settings.OPENROUTER_MODELS


def test_fetch_models_falls_back_on_bad_json():
    def _garbage(url, timeout):
        return b"not json {"

    assert openrouter_models.fetch_models(fetch=_garbage) == settings.OPENROUTER_MODELS


def test_fetch_models_falls_back_when_data_missing():
    def _nodata(url, timeout):
        return b"{}"

    assert openrouter_models.fetch_models(fetch=_nodata) == settings.OPENROUTER_MODELS


def test_live_openrouter_models_fetches_once(monkeypatch):
    calls = {"n": 0}
    sentinel = [("Live", "google/live")]

    def _stub():
        calls["n"] += 1
        return list(sentinel)

    monkeypatch.setattr(openrouter_models, "_cache", None)
    monkeypatch.setattr(openrouter_models, "fetch_models", _stub)
    first = openrouter_models.live_openrouter_models()
    second = openrouter_models.live_openrouter_models()
    assert first == sentinel
    assert second == sentinel
    assert calls["n"] == 1   # cached: fetched exactly once


def test_models_for_openrouter_returns_live_cache(monkeypatch):
    sentinel = [("Live", "google/live")]
    monkeypatch.setattr(openrouter_models, "_cache", None)
    monkeypatch.setattr(openrouter_models, "fetch_models", lambda: list(sentinel))
    assert settings.models_for("openrouter") == sentinel


def test_models_for_claude_is_unchanged():
    assert settings.models_for("claude-subscription") == settings.CLAUDE_MODELS


# ---------------------------------------------------------------------------
# A2: text-only filter, non-dict guard, empty-result fallback
# ---------------------------------------------------------------------------

def test_fetch_models_filters_image_and_code_variants():
    """Image-output and -code-suffix models must be excluded; plain text model kept."""
    data = {
        "data": [
            {
                "id": "google/gemini-3.5-flash",
                "name": "Gemini 3.5 Flash",
                "created": 1730000000,
                "architecture": {"output_modalities": ["text"]},
            },
            {
                "id": "google/gemini-3.1-flash-image",
                "name": "Gemini 3.1 Flash Image",
                "created": 1720000000,
                "architecture": {"output_modalities": ["image", "text"]},
            },
            {
                "id": "moonshotai/kimi-k2.7-code",
                "name": "Kimi K2.7 Code",
                "created": 1710000000,
                "architecture": {"output_modalities": ["text"]},
            },
        ]
    }
    result = openrouter_models.fetch_models(fetch=_fetch_returning(data))
    assert len(result) == 1
    assert result[0][1] == "google/gemini-3.5-flash"


def test_fetch_models_empty_data_returns_fallback():
    """data: [] (all filtered out) must return the curated fallback, not []."""
    result = openrouter_models.fetch_models(fetch=_fetch_returning({"data": []}))
    assert result == list(settings.OPENROUTER_MODELS)


def test_fetch_models_non_dict_entry_survives_without_crash():
    """A non-dict entry (e.g. a bare string) must be skipped; valid dicts kept."""
    data = {
        "data": [
            "junk",
            {"id": "google/gemini-3.5-flash", "name": "Gemini", "created": 1730000000},
        ]
    }
    result = openrouter_models.fetch_models(fetch=_fetch_returning(data))
    # valid dict survives; result is non-empty so fallback is NOT returned
    assert result == [("Gemini", "google/gemini-3.5-flash")]
