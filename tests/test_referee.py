import json

import pytest

from app import config, referee
from app.types import DiceResult, UncertainSpec, RefereeVerdict, BandMeanings

IMPOSSIBLE = '{"kind": "impossible", "reason": "Sheer obsidian wall, no holds.", "uncertain": null}'
TRIVIAL = '{"kind": "trivial", "reason": "The door is already unlocked.", "uncertain": null}'

CHECK = json.dumps({
    "kind": "uncertain",
    "reason": "Picking a guarded lock under time pressure.",
    "uncertain": {
        "mode": "check",
        "attribute_or_track": "Agility",
        "situational_mod": -1,
        "total_mod": 2,
        "table": "wheelhouse",
        "specialty_applies": True,
        "band_meanings": {
            "critical": "Open, silent, and you learn the patrol's route.",
            "success": "The lock yields cleanly.",
            "partial": "It opens, but a tumbler snaps loudly.",
            "failure": "The pick jams; the lock holds.",
            "critical_failure": "The pick breaks off inside and a guard turns.",
        },
        "oracle_options": None,
    },
})

ORACLE = json.dumps({
    "kind": "uncertain",
    "reason": "Whether the merchant is still in town is pure chance.",
    "uncertain": {
        "mode": "oracle",
        "attribute_or_track": "fate",
        "situational_mod": 0,
        "total_mod": 0,
        "table": "standard",
        "specialty_applies": False,
        "band_meanings": None,
        "oracle_options": ["He left at dawn.", "He is at the inn.", "No one has seen him in days."],
    },
})


def test_parse_impossible():
    v = referee.parse_verdict(IMPOSSIBLE)
    assert v.kind == "impossible"
    assert v.uncertain is None


def test_parse_trivial():
    v = referee.parse_verdict(TRIVIAL)
    assert v.kind == "trivial"
    assert v.uncertain is None


def test_parse_uncertain_check():
    v = referee.parse_verdict(CHECK)
    assert v.kind == "uncertain"
    assert v.uncertain.mode == "check"
    assert v.uncertain.total_mod == 2
    assert v.uncertain.table == "wheelhouse"
    assert v.uncertain.specialty_applies is True
    assert v.uncertain.band_meanings.partial == "It opens, but a tumbler snaps loudly."
    assert v.uncertain.oracle_options is None


def test_parse_uncertain_oracle():
    v = referee.parse_verdict(ORACLE)
    assert v.uncertain.mode == "oracle"
    assert v.uncertain.band_meanings is None
    assert v.uncertain.oracle_options[1] == "He is at the inn."


def test_parse_tolerates_fenced_json():
    fenced = "```json\n" + IMPOSSIBLE + "\n```"
    v = referee.parse_verdict(fenced)
    assert v.kind == "impossible"
    assert v.uncertain is None


def test_adjudicate_uses_injected_complete():
    captured = {}

    def fake_complete(role, system, prompt, *, json_out=False):
        captured["role"] = role
        captured["system"] = system
        captured["prompt"] = prompt
        captured["json_out"] = json_out
        return CHECK

    v = referee.adjudicate("RULES", "CHAR", "STATE", "**pick the lock**", complete=fake_complete)
    assert v.kind == "uncertain"
    assert v.uncertain.attribute_or_track == "Agility"
    assert captured["json_out"] is True
    assert captured["system"] == referee.REFEREE_SYSTEM
    assert captured["role"] == config.REFEREE
    assert "**pick the lock**" in captured["prompt"]


def test_resolve_dice_check():
    v = referee.parse_verdict(CHECK)
    calls = {}

    def fake_roll_check(mod, table):
        calls["mod"] = mod
        calls["table"] = table
        return DiceResult(total=9, band="partial")

    result, committed = referee.resolve_dice(v, roll_check=fake_roll_check)
    assert calls["mod"] == 2
    assert calls["table"] == "wheelhouse"
    assert result.band == "partial"
    assert committed == v.uncertain.band_meanings.partial


def test_resolve_dice_oracle():
    v = referee.parse_verdict(ORACLE)

    def fake_roll_oracle(n):
        assert n == 3
        return 1

    result, committed = referee.resolve_dice(v, roll_oracle=fake_roll_oracle)
    assert result.picked_index == 1
    assert result.picked_option == "He is at the inn."
    assert committed == "He is at the inn."


def test_resolve_dice_trivial_is_none():
    v = referee.parse_verdict(TRIVIAL)
    result, committed = referee.resolve_dice(v)
    assert result is None
    assert committed is None


def test_resolve_dice_check_missing_band_meanings_raises():
    v = referee.parse_verdict(CHECK)
    # Override band_meanings to None to simulate LLM schema violation
    v.uncertain.band_meanings = None

    def fake_roll_check(mod, table):
        return DiceResult(total=9, band="partial")

    with pytest.raises(ValueError, match="check verdict is missing band_meanings"):
        referee.resolve_dice(v, roll_check=fake_roll_check)


def test_resolve_dice_oracle_empty_options_raises():
    v = referee.parse_verdict(ORACLE)
    # Override oracle_options to empty list to simulate LLM schema violation
    v.uncertain.oracle_options = []

    def fake_roll_oracle(n):
        # Should not be reached if guard fires first
        return 0

    with pytest.raises(ValueError, match="oracle verdict has no oracle_options"):
        referee.resolve_dice(v, roll_oracle=fake_roll_oracle)
