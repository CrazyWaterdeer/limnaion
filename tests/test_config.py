import pytest

import app.config as config
import app.types as types


def test_types_dataclasses_exist_with_contract_fields():
    verdict = types.RefereeVerdict(kind="trivial", reason="no roll needed")
    assert verdict.kind == "trivial"
    assert verdict.uncertain is None

    spec = types.UncertainSpec(
        mode="check",
        attribute_or_track="grit",
        situational_mod=1,
        total_mod=2,
        table="standard",
        specialty_applies=False,
    )
    assert spec.band_meanings is None
    assert spec.oracle_options is None

    dice = types.DiceResult()
    assert dice.total is None and dice.band is None
    assert dice.picked_index is None and dice.picked_option is None

    bands = types.BandMeanings(
        critical="c", success="s", partial="p",
        failure="f", critical_failure="cf",
    )
    assert bands.critical_failure == "cf"

    update = types.StateUpdate(
        new_state_md="a", log_entry="b",
        world_additions="c", new_compact_state="d",
    )
    assert update.log_entry == "b"

    req = types.NarrationRequest(
        narration_rules="rules",
        recent_turns_raw=[],
        compact_state="state",
        player_input="**look around**",
    )
    assert req.visibility == "hidden"
    assert req.committed_outcome is None

    files = types.GameFiles(
        slug="g", engine="e", rules="r", character="c",
        world="w", state="s", log="l",
    )
    assert files.slug == "g"


def test_framework_paths_resolve_to_existing_files():
    assert config.FRAMEWORK_ROOT.is_dir()
    assert config.ENGINE_MD.is_file()


def test_game_dir_is_under_games_dir():
    assert config.game_dir("foo") == config.GAMES_DIR / "foo"


def test_provider_and_roleconfig_types_exist():
    role = types.RoleConfig(provider="claude-subscription", model="m")
    assert role.provider == "claude-subscription"
    assert role.model == "m"


def test_role_defaults_are_claude_subscription_with_correct_models():
    assert config.NARRATOR == types.RoleConfig("claude-subscription", config.CLAUDE_OPUS)
    assert config.REFEREE == types.RoleConfig("claude-subscription", config.CLAUDE_HAIKU)
    assert config.SCRIBE == types.RoleConfig("claude-subscription", config.CLAUDE_HAIKU)
    # CLAUDE_MODEL keeps its backward-compat name (= CLAUDE_HAIKU).
    assert config.CLAUDE_MODEL == config.CLAUDE_HAIKU


def test_openrouter_base_url_constant():
    assert config.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"


def test_openrouter_api_key_reads_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    assert config.openrouter_api_key() == "sk-or-test"


def test_openrouter_api_key_raises_when_unset(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(KeyError):
        config.openrouter_api_key()
