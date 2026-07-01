"""Live OpenRouter model catalog (no auth) with a curated fallback.

The public https://openrouter.ai/api/v1/models endpoint returns
``{"data": [{"id", "name", "created", ...}, ...]}``. We keep only a few
preferred provider prefixes (OpenRouter lists hundreds), sort newest-first,
cap the list, and present it as ``(label, value)`` pairs for the settings
model dropdown. ANY failure (network, timeout, bad JSON, missing keys) falls
back to the hand-curated ``settings.OPENROUTER_MODELS`` so the UI is never
empty and tests never touch the network. The live result is cached
module-level: we fetch at most once per process.

To avoid an import cycle, this module imports ``app.settings`` only inside the
fallback path; ``settings`` never imports this module at module scope.
"""
from __future__ import annotations

import json
from typing import Callable
from urllib.request import urlopen

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# Only surface these providers in the dropdown.
PREFERRED_PREFIXES = (
    "google/", "openai/", "anthropic/", "deepseek/",
    "moonshotai/", "meta-llama/", "x-ai/",
)

MODEL_CAP = 24

# Module-level cache: None until the first successful (or fallback) fetch.
_cache: list[tuple[str, str]] | None = None


def _default_fetch(url: str, timeout: int) -> bytes:
    """Real HTTP GET of the catalog. Tests inject a fake `fetch` instead."""
    with urlopen(url, timeout=timeout) as resp:  # noqa: S310 (constant https URL, no auth)
        return resp.read()


def _is_text_model(m: dict) -> bool:
    """Keep only text-output chat models — drop image/audio-output and the
    -image/-tts/-audio/-code/-video id variants (suboptimal for narration)."""
    arch = m.get("architecture") or {}
    out = arch.get("output_modalities")
    if isinstance(out, list) and out:
        if "text" not in out or "image" in out or "audio" in out:
            return False
    mid = m.get("id", "")
    return not any(s in mid for s in ("-image", "-tts", "-audio", "-code", "-video"))


def fetch_models(
    *,
    fetch: Callable[[str, int], bytes] = _default_fetch,
    timeout: int = 10,
) -> list[tuple[str, str]]:
    """Return live OpenRouter models as ``(label, value)`` pairs.

    Filters to ``PREFERRED_PREFIXES`` and text-only output modalities, sorts by
    ``created`` descending, caps at ``MODEL_CAP``, and labels each entry by its
    ``name`` (falling back to its ``id``). On ANY exception — or if the filtered
    result is empty — returns ``settings.OPENROUTER_MODELS`` so the UI is never
    empty.
    """
    try:
        payload = json.loads(fetch(OPENROUTER_MODELS_URL, timeout))
        data = payload["data"]
        kept = [
            m for m in data
            if isinstance(m, dict)
            and isinstance(m.get("id"), str)
            and m["id"].startswith(PREFERRED_PREFIXES)
            and _is_text_model(m)
        ]
        kept.sort(key=lambda m: m.get("created", 0), reverse=True)
        result = [((m.get("name") or m["id"]), m["id"]) for m in kept[:MODEL_CAP]]
        if not result:                       # empty success -> use the curated fallback
            from app import settings
            return list(settings.OPENROUTER_MODELS)
        return result
    except Exception:
        from app import settings  # lazy: only on the fallback path
        return list(settings.OPENROUTER_MODELS)


def live_openrouter_models() -> list[tuple[str, str]]:
    """Cached accessor: fetch the live catalog once, reuse it thereafter."""
    global _cache
    if _cache is None:
        _cache = fetch_models()
    return list(_cache)
