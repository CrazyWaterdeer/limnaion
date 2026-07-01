from app import config, game_files, orchestrator
from app.narrator import build_prompt
from app.types import (
    BandMeanings,
    DiceResult,
    NarrationRequest,
    RefereeVerdict,
    StateUpdate,
    UncertainSpec,
)


def _setup_game(tmp_path, monkeypatch):
    """Create a real game dir under a tmp GAMES_DIR and return its slug."""
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    slug = "testgame"
    game_files.new_game_from_templates(slug)
    return slug


def test_play_turn_trivial(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)

    def fake_adjudicate(referee_rules, character_md, compact_state, player_input):
        return RefereeVerdict(kind="trivial", reason="the door is unlocked")

    def fake_resolve_dice(verdict):
        raise AssertionError("resolve_dice must not be called for a trivial verdict")

    def fake_narrate(req):
        return iter(["네, ", "문이 열린다."])

    def fake_record(game, player_input, narration, dice):
        assert dice is None
        return StateUpdate(
            new_state_md="# Current State\n- Scene: the door stands open\n",
            log_entry="## Turn 1 — open door\n- Action: open the door\n",
            world_additions="",
            new_compact_state="COMPACT: the door is open",
        )

    text = orchestrator.play_turn(
        session,
        "**open the door**",
        adjudicate=fake_adjudicate,
        resolve_dice=fake_resolve_dice,
        narrate=fake_narrate,
        record=fake_record,
    )

    assert text == "네, 문이 열린다."
    assert session.compact_state == "COMPACT: the door is open"
    history = session.recent.as_list()
    assert len(history) == 1
    assert "**open the door**" in history[-1]
    assert "문이 열린다." in history[-1]


def test_play_turn_uncertain_passes_committed_outcome(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)

    spec = UncertainSpec(
        mode="check",
        attribute_or_track="Wits",
        situational_mod=0,
        total_mod=1,
        table="standard",
        specialty_applies=False,
        band_meanings=BandMeanings(
            critical="flawless",
            success="it works",
            partial="works at a cost",
            failure="it does not",
            critical_failure="it backfires",
        ),
    )

    def fake_adjudicate(referee_rules, character_md, compact_state, player_input):
        return RefereeVerdict(kind="uncertain", reason="the lock is tricky", uncertain=spec)

    resolve_calls = []

    def fake_resolve_dice(verdict):
        resolve_calls.append(verdict)
        assert verdict.kind == "uncertain"
        return DiceResult(total=9, band="success"), "It works: the lock clicks open"

    captured = {}

    def fake_narrate(req):
        captured["req"] = req
        return iter(["자물쇠가 ", "열린다."])

    def fake_record(game, player_input, narration, dice):
        assert dice is not None
        assert dice.band == "success"
        return StateUpdate(
            new_state_md="# Current State\n",
            log_entry="## Turn 1\n",
            world_additions="",
            new_compact_state="COMPACT: lock open",
        )

    text = orchestrator.play_turn(
        session,
        "**pick the lock**",
        adjudicate=fake_adjudicate,
        resolve_dice=fake_resolve_dice,
        narrate=fake_narrate,
        record=fake_record,
    )

    assert text == "자물쇠가 열린다."
    assert len(resolve_calls) == 1
    req = captured["req"]
    assert isinstance(req, NarrationRequest)
    assert req.committed_outcome == "It works: the lock clicks open"
    assert req.player_input == "**pick the lock**"
    assert session.compact_state == "COMPACT: lock open"


# FIX 1 regression: scribe on turn 2 must see the state written by turn 1.
def test_play_turn_two_turns_scribe_sees_prior_state(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)

    def fake_adjudicate(referee_rules, character_md, compact_state, player_input):
        return RefereeVerdict(kind="trivial", reason="trivial")

    def fake_resolve_dice(verdict):
        raise AssertionError("should not be called")

    def fake_narrate(req):
        return iter(["ok"])

    def fake_record_turn1(game, player_input, narration, dice):
        return StateUpdate(
            new_state_md="STATE_AFTER_TURN_1",
            log_entry="Turn 1; Action: x; Roll: no roll; Outcome: ok; Changes: state",
            world_additions="",
            new_compact_state="COMPACT: after turn 1",
        )

    record_turn2_saw = {}

    def fake_record_turn2(game, player_input, narration, dice):
        record_turn2_saw["state"] = game.state
        return StateUpdate(
            new_state_md="STATE_AFTER_TURN_2",
            log_entry="Turn 2; Action: y; Roll: no roll; Outcome: ok; Changes: state",
            world_additions="",
            new_compact_state="COMPACT: after turn 2",
        )

    orchestrator.play_turn(
        session,
        "**turn 1 action**",
        adjudicate=fake_adjudicate,
        resolve_dice=fake_resolve_dice,
        narrate=fake_narrate,
        record=fake_record_turn1,
    )

    orchestrator.play_turn(
        session,
        "**turn 2 action**",
        adjudicate=fake_adjudicate,
        resolve_dice=fake_resolve_dice,
        narrate=fake_narrate,
        record=fake_record_turn2,
    )

    # Without FIX 1 this would be the template state, not STATE_AFTER_TURN_1.
    assert record_turn2_saw["state"] == "STATE_AFTER_TURN_1"


# FIX 4: build_prompt includes visibility override only when visibility="shown".
def test_build_prompt_visibility_shown_includes_override():
    req = NarrationRequest(
        narration_rules="",
        recent_turns_raw=[],
        compact_state="some state",
        player_input="do thing",
        committed_outcome=None,
        visibility="shown",
    )
    prompt = build_prompt(req)
    assert "수치 공개 모드" in prompt


def test_build_prompt_visibility_hidden_omits_override():
    req = NarrationRequest(
        narration_rules="",
        recent_turns_raw=[],
        compact_state="some state",
        player_input="do thing",
        committed_outcome=None,
        visibility="hidden",
    )
    prompt = build_prompt(req)
    assert "수치 공개 모드" not in prompt


# FIX 5: compress_log is called when log grows past LOG_COMPRESS_THRESHOLD lines.
def test_play_turn_compresses_log_past_threshold(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    # Pre-write a log.md with more than LOG_COMPRESS_THRESHOLD (20) lines.
    long_log = "\n".join(
        f"Turn {i}; Action: thing; Roll: no roll; Outcome: ok; Changes: none"
        for i in range(25)
    )
    game_files.write_text_atomic(config.game_dir(slug) / "log.md", long_log)

    session = orchestrator.load_session(slug)

    def fake_adjudicate(referee_rules, character_md, compact_state, player_input):
        return RefereeVerdict(kind="trivial", reason="trivial")

    def fake_resolve_dice(verdict):
        raise AssertionError("should not be called")

    def fake_narrate(req):
        return iter(["done"])

    def fake_record(game, player_input, narration, dice):
        return StateUpdate(
            new_state_md="# State\n",
            log_entry="Turn 26; Action: x; Roll: no roll; Outcome: ok; Changes: none",
            world_additions="",
            new_compact_state="COMPACT: ok",
        )

    compress_calls = []

    def fake_compress_log(game, **kwargs):
        compress_calls.append(game)
        return "## RECAP\n(compressed)"

    orchestrator.play_turn(
        session,
        "**do something**",
        adjudicate=fake_adjudicate,
        resolve_dice=fake_resolve_dice,
        narrate=fake_narrate,
        record=fake_record,
        compress_log=fake_compress_log,
    )

    assert len(compress_calls) == 1
    log_content = (config.game_dir(slug) / "log.md").read_text(encoding="utf-8")
    assert log_content == "## RECAP\n(compressed)"
