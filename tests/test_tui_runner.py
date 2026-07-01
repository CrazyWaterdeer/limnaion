from app import config, game_files, orchestrator
from app import settings as _settings
from app.tui.runner import PHASES, make_default_runner
from app.types import (
    BandMeanings, DiceResult, RefereeVerdict, RoleConfig, StateUpdate, UncertainSpec,
)


def _setup_game(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    slug = "testgame"
    game_files.new_game_from_templates(slug)
    return slug


def test_phases_constant_order():
    assert PHASES == ("judge", "dice", "narrate", "record")


def test_runner_uncertain_reports_all_phases_and_chunks(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)

    spec = UncertainSpec(
        mode="check", attribute_or_track="Wits", situational_mod=0, total_mod=1,
        table="standard", specialty_applies=False,
        band_meanings=BandMeanings("crit", "ok", "cost", "no", "back"),
    )

    def fake_adjudicate(rules, char, state, inp):
        return RefereeVerdict(kind="uncertain", reason="tricky", uncertain=spec)

    def fake_resolve_dice(verdict):
        return DiceResult(total=9, band="success"), "It works"

    def fake_narrate(req):
        return iter(["자물쇠가 ", "열린다."])

    def fake_record(game, inp, narration, dice):
        return StateUpdate("# State\n", "Turn 1\n", "", "COMPACT")

    runner = make_default_runner(
        adjudicate=fake_adjudicate, resolve_dice=fake_resolve_dice,
        narrate=fake_narrate, record=fake_record,
    )

    phases, chunks = [], []
    text = runner(session, "**pick the lock**",
                  on_phase=phases.append, on_chunk=chunks.append)

    assert phases == ["judge", "dice", "narrate", "record"]
    assert chunks == ["자물쇠가 ", "열린다."]
    assert "".join(chunks) == text == "자물쇠가 열린다."


def test_runner_trivial_skips_dice_phase(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)

    def fake_adjudicate(rules, char, state, inp):
        return RefereeVerdict(kind="trivial", reason="easy")

    def fake_resolve_dice(verdict):
        raise AssertionError("resolve_dice must not run for trivial")

    def fake_narrate(req):
        return iter(["문이 ", "열린다."])

    def fake_record(game, inp, narration, dice):
        return StateUpdate("# State\n", "Turn 1\n", "", "COMPACT")

    runner = make_default_runner(
        adjudicate=fake_adjudicate, resolve_dice=fake_resolve_dice,
        narrate=fake_narrate, record=fake_record,
    )

    phases = []
    text = runner(session, "**open the door**", on_phase=phases.append, on_chunk=lambda c: None)

    assert phases == ["judge", "narrate", "record"]
    assert text == "문이 열린다."


def test_runner_passes_settings_roles_and_length(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)

    # Pre-write a long log so the compression path triggers (threshold = 20 lines).
    long_log = "\n".join(
        f"Turn {i}; Action: x; Roll: no roll; Outcome: ok; Changes: none" for i in range(25)
    )
    game_files.write_text_atomic(config.game_dir(slug) / "log.md", long_log)
    session = orchestrator.load_session(slug)   # reload so the long log is in session.game

    s = _settings.default_settings()
    s.referee = RoleConfig("openrouter", "ref-model")
    s.narrator = RoleConfig("openrouter", "narr-model")
    s.scribe = RoleConfig("openrouter", "scribe-model")
    s.narration_length = "long"

    seen = {}

    def fake_adjudicate(*args, role=None):
        seen["referee_role"] = role
        return RefereeVerdict(kind="trivial", reason="ok")

    def fake_resolve_dice(verdict):
        raise AssertionError("trivial -> no dice")

    def fake_narrate(req, *, role=None, length=None):
        seen["narrator_role"] = role
        seen["length"] = length
        return iter(["네."])

    def fake_record(*args, role=None):
        seen["scribe_role"] = role
        return StateUpdate("# State\n", "Turn 1\n", "", "COMPACT")

    def fake_compress(game, *, keep_n=10, role=None):
        seen["compress_role"] = role
        return game.log

    runner = make_default_runner(
        settings=s, adjudicate=fake_adjudicate, resolve_dice=fake_resolve_dice,
        narrate=fake_narrate, record=fake_record, compress_log=fake_compress,
    )
    runner(session, "**do**", on_phase=lambda p: None, on_chunk=lambda c: None)

    assert seen["referee_role"] == s.referee
    assert seen["narrator_role"] == s.narrator
    assert seen["scribe_role"] == s.scribe
    assert seen["length"] == "long"
    assert seen["compress_role"] == s.scribe


def test_runner_without_settings_passes_no_role_kwargs(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)

    calls = {}

    def fake_adjudicate(*args):           # NOTE: no role kwarg accepted
        calls["adj_args"] = len(args)
        return RefereeVerdict(kind="trivial", reason="ok")

    def fake_narrate(req):                # NOTE: no role/length kwargs accepted
        return iter(["ok"])

    def fake_record(*args):
        return StateUpdate("# State\n", "Turn 1\n", "", "COMPACT")

    runner = make_default_runner(
        adjudicate=fake_adjudicate, resolve_dice=lambda v: None,
        narrate=fake_narrate, record=fake_record,
    )
    # Must not raise TypeError from injecting unexpected role/length kwargs.
    text = runner(session, "**do**", on_phase=lambda p: None, on_chunk=lambda c: None)
    assert text == "ok"
    assert calls["adj_args"] == 4
