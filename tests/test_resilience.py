# tests/test_resilience.py
import subprocess

import pytest

from app import config, game_files, orchestrator, providers
from app.providers import ModelError
from app.types import RefereeVerdict, StateUpdate


def _setup_game(tmp_path, monkeypatch):
    """Create a real game dir under a tmp GAMES_DIR and return its slug (Task 9 style)."""
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    slug = "testgame"
    game_files.new_game_from_templates(slug)
    return slug


# (a) _retry: one initial call + one retry, then ModelError.
def test_retry_retries_once_then_raises_model_error():
    calls = []

    def failing():
        calls.append(1)
        raise RuntimeError("boom")

    with pytest.raises(ModelError):
        providers._retry(failing, attempts=2)
    assert len(calls) == 2  # one initial attempt + exactly one retry


# (b) claude_complete wraps a failing subprocess into ModelError after one retry.
def test_claude_complete_raises_model_error_after_failing_subprocess(monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        raise subprocess.CalledProcessError(returncode=1, cmd=argv)

    monkeypatch.setattr(providers.subprocess, "run", fake_run)
    with pytest.raises(ModelError):
        providers.claude_complete("m", "SYS", "PROMPT")
    assert len(calls) == 2  # retried once before giving up


# (c) adjudicate fails -> no-roll downgrade; turn still narrates and completes.
def test_play_turn_adjudicate_failure_downgrades_to_no_roll(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)

    def fake_adjudicate(referee_rules, character_md, compact_state, player_input):
        raise ModelError("referee unavailable")

    def fake_resolve_dice(verdict):
        raise AssertionError("resolve_dice must NOT run when adjudicate failed")

    def fake_narrate(req):
        assert req.committed_outcome is None  # downgraded: no committed outcome
        return iter(["계속 ", "진행된다."])

    record_dice = []

    def fake_record(game, player_input, narration, dice):
        record_dice.append(dice)
        assert dice is None  # no roll happened
        return StateUpdate(
            new_state_md="S", log_entry="L", world_additions="",
            new_compact_state="COMPACT: ok",
        )

    text = orchestrator.play_turn(
        session,
        "**do a thing**",
        adjudicate=fake_adjudicate,
        resolve_dice=fake_resolve_dice,
        narrate=fake_narrate,
        record=fake_record,
    )

    assert text == "계속 진행된다."          # narration still produced
    assert record_dice == [None]             # no dice rolled this turn
    assert session.compact_state == "COMPACT: ok"
    assert "**do a thing**" in session.recent.as_list()[-1]


# (d) narrate fails -> honest sentinel; record is NEVER called and state is untouched.
def test_play_turn_narrate_failure_returns_sentinel_and_skips_record(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)
    before_state = session.compact_state

    def fake_adjudicate(referee_rules, character_md, compact_state, player_input):
        return RefereeVerdict(kind="trivial", reason="trivial action")

    def fake_resolve_dice(verdict):
        raise AssertionError("resolve_dice must NOT run on a trivial verdict")

    narrate_calls = {"n": 0}

    def fake_narrate(req):
        # Stands in for a narrator that failed its original attempt AND its one
        # internal backend retry -> stream_gemini raised ModelError (failed twice).
        narrate_calls["n"] += 1
        raise ModelError("narrator unavailable")

    def fake_record(game, player_input, narration, dice):
        raise AssertionError("record must NOT run when narration failed")

    text = orchestrator.play_turn(
        session,
        "**look around**",
        adjudicate=fake_adjudicate,
        resolve_dice=fake_resolve_dice,
        narrate=fake_narrate,
        record=fake_record,
    )

    assert text == "(서술 생성에 실패했습니다 — 다시 시도해 주세요.)"
    assert narrate_calls["n"] == 1            # play_turn does not add its own retry
    assert session.recent.as_list() == []     # no fabricated turn recorded
    assert session.compact_state == before_state  # state untouched


# (e) record fails -> narration is KEPT (recent appended, text returned), state unchanged.
def test_play_turn_record_failure_keeps_narration_and_appends_recent(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)
    before_state = session.compact_state

    def fake_adjudicate(referee_rules, character_md, compact_state, player_input):
        return RefereeVerdict(kind="trivial", reason="trivial action")

    def fake_resolve_dice(verdict):
        raise AssertionError("resolve_dice must NOT run on a trivial verdict")

    def fake_narrate(req):
        return iter(["문이 ", "열린다."])

    def fake_record(game, player_input, narration, dice):
        raise ModelError("scribe unavailable")

    text = orchestrator.play_turn(
        session,
        "**open the door**",
        adjudicate=fake_adjudicate,
        resolve_dice=fake_resolve_dice,
        narrate=fake_narrate,
        record=fake_record,
    )

    assert text == "문이 열린다."             # narration the player saw is kept
    history = session.recent.as_list()
    assert len(history) == 1
    assert "**open the door**" in history[-1]
    assert "문이 열린다." in history[-1]
    assert session.compact_state == before_state  # state update skipped (re-recordable later)
