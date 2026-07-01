"""Task 6 — epilogue wiring, splash-by-default routing, optional TUI slug, frog body."""
from textual.app import App
from textual.widgets import Static

from app import config, game_files, orchestrator, persona
from app.settings import default_settings
from app.tui.app import LimnaionApp
from app.tui.runner import make_default_runner
from app.tui.screens.epilogue import EpilogueScreen
from app.tui.screens.play import PlayScreen
from app.tui.screens.splash import SplashScreen
from app.types import RefereeVerdict, StateUpdate


def _setup_game(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    slug = "testgame"
    game_files.new_game_from_templates(slug)
    return slug


def _fake_runner(session, player_input, *, on_phase, on_chunk):
    on_phase("judge")
    on_phase("narrate")
    on_chunk("끝.")
    on_phase("record")
    return "끝."


class _EpiHost(App):
    """Minimal host so an EpilogueScreen can be driven in isolation."""

    def __init__(self, screen, **kwargs) -> None:
        super().__init__(**kwargs)
        self._screen = screen

    def get_default_screen(self):
        return self._screen


# --- app routing -----------------------------------------------------------

async def test_app_no_slug_shows_splash(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    app = LimnaionApp()                       # no slug -> hub
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, SplashScreen)


async def test_app_with_slug_shows_play(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, PlayScreen)


# --- epilogue screen -------------------------------------------------------

async def test_epilogue_screen_renders_open_body_close(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)
    screen = EpilogueScreen(session, compose_body=lambda game, **kw: "늪의 물이 잔잔해진다.")
    app = _EpiHost(screen)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()  # B1: deterministic worker wait
        await pilot.pause()
        blob = "\n".join(s.content for s in app.screen.query(Static))
        assert persona.EPILOGUE_OPEN in blob
        assert "늪의 물이 잔잔해진다." in blob
        assert persona.EPILOGUE_CLOSE in blob


async def test_ctrl_e_opens_epilogue_and_escape_returns_to_splash(tmp_path, monkeypatch):
    import app.tui.screens.epilogue as epilogue_mod

    slug = _setup_game(tmp_path, monkeypatch)
    real_cls = epilogue_mod.EpilogueScreen
    # action_epilogue lazily imports EpilogueScreen from the module, so patching the
    # module attribute lets us inject a fake compose_body (no real model is called).
    monkeypatch.setattr(
        epilogue_mod, "EpilogueScreen",
        lambda session, *, settings=None: real_cls(
            session, settings=settings,
            compose_body=lambda game, **kw: "개구리가 마지막 노래를 부른다.",
        ),
    )
    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, PlayScreen)
        await pilot.press("ctrl+e")
        await app.workers.wait_for_complete()  # B1: deterministic worker wait
        await pilot.pause()
        assert isinstance(app.screen, real_cls)
        blob = "\n".join(s.content for s in app.screen.query(Static))
        assert persona.EPILOGUE_OPEN in blob
        assert "개구리가 마지막 노래를 부른다." in blob
        assert persona.EPILOGUE_CLOSE in blob
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, SplashScreen)


# --- frog-tone body threading ---------------------------------------------

def _run_one_turn(tmp_path, monkeypatch, frog_tone, fake_narrate):
    slug = _setup_game(tmp_path, monkeypatch)
    session = orchestrator.load_session(slug)
    s = default_settings()
    s.frog_tone = frog_tone

    def fake_adjudicate(rules, char, state, inp, *, role=None):
        return RefereeVerdict(kind="trivial", reason="easy")

    def fake_record(game, inp, narration, dice, *, role=None):
        return StateUpdate("# State\n", "Turn 1\n", "", "COMPACT")

    runner = make_default_runner(
        settings=s, adjudicate=fake_adjudicate,
        resolve_dice=lambda v: None, narrate=fake_narrate, record=fake_record,
    )
    runner(session, "**wait**", on_phase=lambda p: None, on_chunk=lambda c: None)


def test_runner_frog_always_threads_frog_system(tmp_path, monkeypatch):
    seen = {}

    def fake_narrate(req, *, role=None, length=None, frog_system=""):
        seen["frog_system"] = frog_system
        return iter(["네."])

    _run_one_turn(tmp_path, monkeypatch, "always", fake_narrate)
    assert seen["frog_system"] == persona.FROG_SYSTEM


def test_runner_frog_bookends_keeps_body_pure(tmp_path, monkeypatch):
    # fake_narrate does NOT accept frog_system: if the runner injected it for a
    # non-"always" tone, this would raise TypeError. bookends leaves the body pure.
    def fake_narrate(req, *, role=None, length=None):
        return iter(["네."])

    _run_one_turn(tmp_path, monkeypatch, "bookends", fake_narrate)
