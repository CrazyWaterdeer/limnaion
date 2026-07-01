import json

from app import config, scribe
from app.types import DiceResult, GameFiles, StateUpdate

SAMPLE = {
    "new_state_md": "# Current State: Test\n- **Last turn #:** 7",
    "log_entry": (
        "Turn 7; Action: pick the lock; Roll: Check PARTIAL; "
        "Outcome: lock gives but a pin snaps; Changes: HP 8->7"
    ),
    "world_additions": "## Key NPCs\n- **Warden** — suspicious; patrols the east wing",
    "new_compact_state": "At the cell door, lock half-open, a guard approaching from the hall.",
}


def _game(**over):
    base = dict(
        slug="test", engine="E", rules="R", character="C",
        world="W", state="S", log="L",
    )
    base.update(over)
    return GameFiles(**base)


def test_parse_state_update_plain_json():
    su = scribe.parse_state_update(json.dumps(SAMPLE))
    assert isinstance(su, StateUpdate)
    assert su.new_state_md == SAMPLE["new_state_md"]
    assert su.log_entry == SAMPLE["log_entry"]
    assert su.world_additions == SAMPLE["world_additions"]
    assert su.new_compact_state == SAMPLE["new_compact_state"]


def test_parse_state_update_strips_fence_and_prose():
    raw = "Sure, here:\n```json\n" + json.dumps(SAMPLE) + "\n```\nDone."
    su = scribe.parse_state_update(raw)
    assert su.new_compact_state == SAMPLE["new_compact_state"]


def test_parse_state_update_missing_world_additions_defaults_empty():
    data = {k: v for k, v in SAMPLE.items() if k != "world_additions"}
    su = scribe.parse_state_update(json.dumps(data))
    assert su.world_additions == ""


def test_record_builds_prompt_and_parses():
    seen = {}

    def fake_complete(role, system, prompt, *, json_out=False):
        seen.update(role=role, system=system, prompt=prompt, json_out=json_out)
        return json.dumps(SAMPLE)

    game = _game(state="STATE-BODY", log="LOG-BODY", world="WORLD-BODY")
    dice = DiceResult(total=7, band="partial")
    su = scribe.record(game, "**pick the lock**", "The pin snaps under the pick...", dice, complete=fake_complete)

    assert isinstance(su, StateUpdate)
    assert su.log_entry == SAMPLE["log_entry"]
    assert seen["json_out"] is True
    assert seen["system"] == scribe.SCRIBE_SYSTEM
    assert seen["role"] == config.SCRIBE
    for needle in ("STATE-BODY", "LOG-BODY", "WORLD-BODY", "**pick the lock**", "partial", "7"):
        assert needle in seen["prompt"], needle


def test_record_no_roll_marks_no_roll():
    captured = {}

    def fake_complete(role, system, prompt, *, json_out=False):
        captured["prompt"] = prompt
        return json.dumps(SAMPLE)

    su = scribe.record(_game(), "I look around the cell", "Damp stone, a barred window...", None, complete=fake_complete)
    assert "no roll" in captured["prompt"]
    assert su.new_state_md == SAMPLE["new_state_md"]


def test_record_oracle_pick_in_prompt():
    captured = {}

    def fake_complete(role, system, prompt, *, json_out=False):
        captured["prompt"] = prompt
        return json.dumps(SAMPLE)

    dice = DiceResult(picked_index=2, picked_option="A stranger arrives")
    scribe.record(_game(), "(oracle) is anyone here?", "Footsteps...", dice, complete=fake_complete)
    assert "A stranger arrives" in captured["prompt"]


def test_compress_log_returns_injected_text():
    new_log = "# Play Log: Test\n\n## RECAP (Turns 1-12)\n- key facts kept\n\n## Turn 13 — now\n"
    seen = {}

    def fake_complete(role, system, prompt, *, json_out=False):
        seen.update(json_out=json_out, prompt=prompt, system=system, role=role)
        return new_log

    out = scribe.compress_log(_game(log="OLD-LOG-BODY"), keep_n=5, complete=fake_complete)
    assert out == new_log
    assert seen["json_out"] is False
    assert seen["role"] == config.SCRIBE
    assert "OLD-LOG-BODY" in seen["prompt"]
    assert "5" in seen["prompt"]
    assert "RECAP" in seen["system"]
