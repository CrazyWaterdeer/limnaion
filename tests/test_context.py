import inspect

from app.context import RecentTurns, build_narration_request, referee_context
from app.types import NarrationRequest


def test_recent_turns_caps_at_k_newest_last():
    recent = RecentTurns(k=3)
    for i in range(5):  # add k+2 = 5 exchanges
        recent.add(f"action {i}", f"narration {i}")
    items = recent.as_list()
    # only k kept
    assert len(items) == 3
    # newest is last
    assert "action 4" in items[-1]
    assert "narration 4" in items[-1]
    # oldest kept is turn 2; turns 0 and 1 were dropped
    assert "action 2" in items[0]
    joined = "\n".join(items)
    assert "action 0" not in joined
    assert "action 1" not in joined


def test_build_narration_request_copies_recent_and_carries_outcome():
    recent = RecentTurns(k=6)
    recent.add("look around", "You see a dim hall.")
    req = build_narration_request(
        narration_rules="RULES",
        recent=recent,
        compact_state="STATE",
        player_input="open the door",
        committed_outcome="partial: the door creaks open halfway",
        visibility="hidden",
    )
    assert isinstance(req, NarrationRequest)
    # recent.as_list() is copied verbatim into recent_turns_raw
    assert req.recent_turns_raw == recent.as_list()
    # committed_outcome is carried through
    assert req.committed_outcome == "partial: the door creaks open halfway"
    assert req.narration_rules == "RULES"
    assert req.compact_state == "STATE"
    assert req.player_input == "open the door"
    assert req.visibility == "hidden"


def test_referee_context_excludes_raw_narration():
    # The SAME narration text must reach the Gemini request (layer 1) but never
    # the Claude referee context (layer 2).
    sentinel = "NARRATION_SENTINEL_q7x"
    recent = RecentTurns(k=6)
    recent.add("the player acted", f"a vivid beat containing {sentinel}")

    # Layer 1: build_narration_request carries the raw narration.
    req = build_narration_request(
        "NARRATION_RULES", recent, "COMPACT STATE", "**do a thing**", None, "hidden"
    )
    assert any(sentinel in line for line in req.recent_turns_raw)

    # Layer 2: referee_context never carries narration (it has no channel for it).
    ctx = referee_context("REFEREE_RULES", "CHARACTER SHEET", "COMPACT STATE", "**do a thing**")
    assert sentinel not in ctx

    # Structural guard: referee_context exposes no parameter that could receive
    # narration / recent turns. If a future change adds one, this fails.
    params = set(inspect.signature(referee_context).parameters)
    assert params == {"referee_rules", "character_md", "compact_state", "player_input"}
