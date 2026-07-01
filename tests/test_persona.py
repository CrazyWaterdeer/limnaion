"""Tests for app/persona.py — Brekekos persona constants and generation helpers."""
from __future__ import annotations

import pytest
from app.types import GameFiles
from app import config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ConstantRng:
    """Always returns the first element — deterministic, no randomness."""
    def choice(self, seq):
        return seq[0]


class _RecordingRng:
    """Records every call to choice; returns the first element."""
    def __init__(self):
        self.calls: list[list] = []

    def choice(self, seq):
        self.calls.append(list(seq))
        return seq[0]


def _make_game(**overrides) -> GameFiles:
    defaults = dict(
        slug="test",
        engine="# engine",
        rules="# rules",
        character="# character",
        world="# world",
        state="## State\n현재 상태: 낡은 배 위에서 흔들리는 중.",
        log="## Log\n[Turn 1] 여정의 첫 노질이 시작되었다.",
    )
    defaults.update(overrides)
    return GameFiles(**defaults)


# ---------------------------------------------------------------------------
# Module-level constant smoke tests
# ---------------------------------------------------------------------------

def test_splash_art_is_non_empty_string():
    from app import persona
    assert isinstance(persona.SPLASH_ART, str) and persona.SPLASH_ART.strip()


def test_splash_greeting_is_non_empty_string():
    from app import persona
    assert isinstance(persona.SPLASH_GREETING, str) and persona.SPLASH_GREETING.strip()


def test_splash_greeting_short_is_non_empty_string():
    from app import persona
    assert isinstance(persona.SPLASH_GREETING_SHORT, str) and persona.SPLASH_GREETING_SHORT.strip()


def test_crossing_transition_is_non_empty_string():
    from app import persona
    assert isinstance(persona.CROSSING_TRANSITION, str) and persona.CROSSING_TRANSITION.strip()


def test_epilogue_open_is_non_empty_string():
    from app import persona
    assert isinstance(persona.EPILOGUE_OPEN, str) and persona.EPILOGUE_OPEN.strip()


def test_epilogue_close_is_non_empty_string():
    from app import persona
    assert isinstance(persona.EPILOGUE_CLOSE, str) and persona.EPILOGUE_CLOSE.strip()


def test_frog_system_is_non_empty_string():
    from app import persona
    assert isinstance(persona.FROG_SYSTEM, str) and len(persona.FROG_SYSTEM) > 20


def test_epilogue_system_is_non_empty_string():
    from app import persona
    assert isinstance(persona.EPILOGUE_SYSTEM, str) and len(persona.EPILOGUE_SYSTEM) > 20


# ---------------------------------------------------------------------------
# LOADING_POOLS structure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["judge", "dice", "narrate", "record"])
def test_loading_pool_key_exists_and_is_non_empty(key):
    from app import persona
    assert key in persona.LOADING_POOLS
    assert isinstance(persona.LOADING_POOLS[key], list)
    assert len(persona.LOADING_POOLS[key]) > 0


@pytest.mark.parametrize("key", ["judge", "dice", "narrate", "record"])
def test_loading_pool_entries_are_non_empty_strings(key):
    from app import persona
    for item in persona.LOADING_POOLS[key]:
        assert isinstance(item, str) and item.strip(), f"Empty entry in pool '{key}': {item!r}"


def test_loading_pools_has_exactly_four_keys():
    from app import persona
    assert set(persona.LOADING_POOLS.keys()) == {"judge", "dice", "narrate", "record"}


# ---------------------------------------------------------------------------
# ONBOARDING_BEATS structure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["opening", "name", "concept", "strengths", "scene"])
def test_onboarding_beat_key_exists_and_is_non_empty(key):
    from app import persona
    assert key in persona.ONBOARDING_BEATS
    assert isinstance(persona.ONBOARDING_BEATS[key], str)
    assert persona.ONBOARDING_BEATS[key].strip()


def test_onboarding_beats_has_exactly_five_keys():
    from app import persona
    assert set(persona.ONBOARDING_BEATS.keys()) == {
        "opening", "name", "concept", "strengths", "scene"
    }


# ---------------------------------------------------------------------------
# pick_loading_line
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phase", ["judge", "dice", "narrate", "record"])
def test_pick_loading_line_returns_pool_member(phase):
    from app import persona
    result = persona.pick_loading_line(phase, rng=_ConstantRng())
    assert result in persona.LOADING_POOLS[phase]


def test_pick_loading_line_returns_empty_for_idle():
    from app import persona
    assert persona.pick_loading_line("idle") == ""


def test_pick_loading_line_returns_empty_for_unknown_phase():
    from app import persona
    assert persona.pick_loading_line("totally_unknown_phase_xyz") == ""


def test_pick_loading_line_calls_rng_choice_with_pool():
    from app import persona
    rng = _RecordingRng()
    persona.pick_loading_line("judge", rng=rng)
    assert len(rng.calls) == 1
    assert rng.calls[0] == persona.LOADING_POOLS["judge"]


def test_pick_loading_line_calls_rng_choice_with_narrate_pool():
    from app import persona
    rng = _RecordingRng()
    persona.pick_loading_line("narrate", rng=rng)
    assert rng.calls[0] == persona.LOADING_POOLS["narrate"]


# ---------------------------------------------------------------------------
# epilogue_body
# ---------------------------------------------------------------------------

def test_epilogue_body_returns_complete_output():
    from app import persona
    game = _make_game()

    def fake_complete(role, system, prompt):
        return "에필로그 본문이 흘러나온다."

    result = persona.epilogue_body(game, role=config.NARRATOR, complete=fake_complete)
    assert result == "에필로그 본문이 흘러나온다."


def test_epilogue_body_prompt_contains_state():
    from app import persona
    game = _make_game(state="## State\n독특한_상태_마커_XYZ")
    captured_prompt = []

    def fake_complete(role, system, prompt):
        captured_prompt.append(prompt)
        return "done"

    persona.epilogue_body(game, complete=fake_complete)
    assert "독특한_상태_마커_XYZ" in captured_prompt[0]


def test_epilogue_body_prompt_contains_log():
    from app import persona
    game = _make_game(log="## Log\n독특한_로그_마커_ABC")
    captured_prompt = []

    def fake_complete(role, system, prompt):
        captured_prompt.append(prompt)
        return "done"

    persona.epilogue_body(game, complete=fake_complete)
    assert "독특한_로그_마커_ABC" in captured_prompt[0]


def test_epilogue_body_system_contains_epilogue_system():
    from app import persona
    captured_system = []

    def fake_complete(role, system, prompt):
        captured_system.append(system)
        return "done"

    persona.epilogue_body(game=_make_game(), complete=fake_complete)
    assert len(captured_system) == 1
    # EPILOGUE_SYSTEM must be represented in the combined system string
    assert persona.EPILOGUE_SYSTEM[:30] in captured_system[0]


def test_epilogue_body_system_contains_frog_system():
    from app import persona
    captured_system = []

    def fake_complete(role, system, prompt):
        captured_system.append(system)
        return "done"

    persona.epilogue_body(game=_make_game(), complete=fake_complete)
    assert persona.FROG_SYSTEM[:30] in captured_system[0]


def test_epilogue_body_passes_role_to_complete():
    from app import persona
    from app.types import RoleConfig
    captured_role = []

    def fake_complete(role, system, prompt):
        captured_role.append(role)
        return "done"

    custom_role = RoleConfig("claude-subscription", "test-model")
    persona.epilogue_body(game=_make_game(), role=custom_role, complete=fake_complete)
    assert captured_role[0] is custom_role


def test_epilogue_body_complete_called_exactly_once():
    from app import persona
    call_count = []

    def fake_complete(role, system, prompt):
        call_count.append(1)
        return "done"

    persona.epilogue_body(game=_make_game(), complete=fake_complete)
    assert sum(call_count) == 1


# ---------------------------------------------------------------------------
# A2 — EPILOGUE_SYSTEM no-numbers prohibition
# ---------------------------------------------------------------------------

def test_epilogue_system_contains_no_numbers_prohibition():
    """A2: EPILOGUE_SYSTEM must forbid echoing raw numbers (HP, stats, turn count, etc.)."""
    from app import persona
    # Either Korean term for numbers/stats is acceptable.
    has_guard = "숫자" in persona.EPILOGUE_SYSTEM or "수치" in persona.EPILOGUE_SYSTEM
    assert has_guard, (
        "EPILOGUE_SYSTEM must contain a no-numbers prohibition "
        "('수치' or '숫자' expected)"
    )


# ---------------------------------------------------------------------------
# onboarding_ack
# ---------------------------------------------------------------------------

def test_onboarding_ack_name_echoes_answer():
    from app.persona import onboarding_ack
    result = onboarding_ack("name", "진")
    assert "진" in result


def test_onboarding_ack_unknown_beat_returns_empty():
    from app.persona import onboarding_ack
    assert onboarding_ack("scene", "x") == ""


def test_onboarding_ack_all_three_keys_exist():
    from app import persona
    for key in ("name", "concept", "strengths"):
        assert key in persona.ONBOARDING_ACKS


# ---------------------------------------------------------------------------
# A3 — epilogue_body frog= flag
# ---------------------------------------------------------------------------

def test_epilogue_body_frog_false_excludes_frog_system():
    """A3: frog=False must omit FROG_SYSTEM from the combined system string."""
    from app import persona
    captured_system: list[str] = []

    def fake_complete(role, system, prompt):
        captured_system.append(system)
        return "done"

    persona.epilogue_body(game=_make_game(), frog=False, complete=fake_complete)
    assert len(captured_system) == 1
    assert persona.FROG_SYSTEM not in captured_system[0], (
        "frog=False: FROG_SYSTEM must NOT appear in the system string"
    )


def test_epilogue_body_frog_true_includes_frog_system():
    """A3: frog=True (the default) must include FROG_SYSTEM in the combined system string."""
    from app import persona
    captured_system: list[str] = []

    def fake_complete(role, system, prompt):
        captured_system.append(system)
        return "done"

    persona.epilogue_body(game=_make_game(), frog=True, complete=fake_complete)
    assert len(captured_system) == 1
    assert persona.FROG_SYSTEM[:30] in captured_system[0], (
        "frog=True: FROG_SYSTEM must appear in the system string"
    )
