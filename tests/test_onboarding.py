import json
from pathlib import Path

import pytest

from app import config, onboarding
from app.onboarding import OnboardingInputs


# ---------------------------------------------------------------------------
# B5: TEMPLATES_DIR isolation — provide minimal stub templates so these unit
# tests are self-contained and do not depend on the real templates/ directory.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _stub_templates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect config.TEMPLATES_DIR to a tmp dir with minimal stub files."""
    tpl_dir = tmp_path / "_templates"
    tpl_dir.mkdir()
    (tpl_dir / "character.md").write_text("# Character Template\n## Concept\n")
    (tpl_dir / "world.md").write_text("# World Template\n## Setting\n")
    (tpl_dir / "state.md").write_text("# State Template\n## Scene\n")
    (tpl_dir / "rules.md").write_text("# Rules\n")
    (tpl_dir / "log.md").write_text("# Log\n")
    monkeypatch.setattr(config, "TEMPLATES_DIR", tpl_dir)

SAMPLE = {
    "title": "철문 너머의 빚",
    "character_md": (
        "# Character: Mira\n\n## Concept\nA hedge-witch who reads the tide\n\n"
        "## Attributes  (hidden)\n- **Might** +0\n- **Agility** +1\n- **Wits** +2\n- **Presence** +1\n\n"
        "## Specialties\n- Omen-reading\n- Breath-holding\n"
    ),
    "world_md": (
        "## Setting\nA drowned village where the tide never fully leaves.\n"
    ),
    "state_md": (
        "# Current State: The Sunken Fen\n\n- **Scene:** dusk on the jetty\n"
        "- **Condition:** HP 8/8\n- **Last turn #:** 0\n"
    ),
    "opening_scene": "물안개가 잔교를 삼키고, 너는 썩은 널빤지 위에 홀로 선다.",
}


def _inputs():
    return OnboardingInputs(
        name="Mira",
        concept="A hedge-witch who reads the tide",
        background="Orphaned by the flood; raised by the fen herons",
        strengths="Reads omens; calm under water",
        weaknesses="Frail; haunted by the drowned",
        scene="Dusk on a rotting jetty as the fog rolls in",
    )


def test_create_game_writes_files_and_returns_scene(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    seen = {}

    def fake_complete(role, system, prompt, *, json_out=False):
        seen.update(role=role, system=system, prompt=prompt, json_out=json_out)
        return json.dumps(SAMPLE)

    scene = onboarding.create_game("mira", _inputs(), complete=fake_complete)

    assert scene == SAMPLE["opening_scene"]
    assert seen["json_out"] is True
    assert seen["system"] == onboarding.CREATOR_SYSTEM
    assert seen["role"] == config.SCRIBE
    # the player's authored fiction is handed to the model verbatim
    for needle in ("Mira", "hedge-witch", "rotting jetty", "Frail"):
        assert needle in seen["prompt"], needle

    d = config.game_dir("mira")
    assert (d / "character.md").read_text(encoding="utf-8") == SAMPLE["character_md"]
    world_text = (d / "world.md").read_text(encoding="utf-8")
    assert world_text.startswith(f"# {SAMPLE['title']}")
    assert SAMPLE["world_md"] in world_text
    assert (d / "state.md").read_text(encoding="utf-8") == SAMPLE["state_md"]
    # rules.md and log.md still come from the template scaffold, untouched
    assert (d / "rules.md").exists()
    assert (d / "log.md").exists()


def test_create_game_strips_json_code_fence(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)

    def fake_complete(role, system, prompt, *, json_out=False):
        return "```json\n" + json.dumps(SAMPLE) + "\n```"

    scene = onboarding.create_game("fenced", _inputs(), complete=fake_complete)
    assert scene == SAMPLE["opening_scene"]
    d = config.game_dir("fenced")
    world_text = (d / "world.md").read_text(encoding="utf-8")
    assert world_text.startswith(f"# {SAMPLE['title']}")


def test_create_game_raises_on_missing_key(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    partial = {k: v for k, v in SAMPLE.items() if k != "state_md"}

    def fake_complete(role, system, prompt, *, json_out=False):
        return json.dumps(partial)

    with pytest.raises(ValueError):
        onboarding.create_game("broken", _inputs(), complete=fake_complete)
    # validation precedes any disk write: nothing was scaffolded for the broken game
    assert not config.game_dir("broken").exists()


def test_create_game_raises_on_missing_title(tmp_path, monkeypatch):
    """C1a: 'title' is now required; omitting it must raise ValueError before any disk write."""
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    partial = {k: v for k, v in SAMPLE.items() if k != "title"}

    def fake_complete(role, system, prompt, *, json_out=False):
        return json.dumps(partial)

    with pytest.raises(ValueError):
        onboarding.create_game("no-title", _inputs(), complete=fake_complete)
    assert not config.game_dir("no-title").exists()


def test_create_game_raises_on_malformed_json(tmp_path, monkeypatch):
    """B8: malformed model output must raise JSONDecodeError and leave no game dir."""
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)

    def fake_complete(role, system, prompt, *, json_out=False):
        return "not valid json"

    with pytest.raises(json.JSONDecodeError):
        onboarding.create_game("bad-json", _inputs(), complete=fake_complete)
    # no game dir must have been created
    assert not config.game_dir("bad-json").exists()
