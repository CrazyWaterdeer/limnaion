"""Tests for SplashScreen: game list, navigation actions, rendered art/greeting."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Static

from app import config, game_files
from app.settings import default_settings
from app.tui.screens.load_game import LoadGameScreen
from app.tui.screens.settings import SettingsScreen
from app.tui.screens.splash import SplashScreen


class _FakeOnboardingScreen(Screen):
    """Minimal stand-in for OnboardingScreen; injected so tests run before Task D5."""

    def __init__(self, *, settings=None, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Static("fake onboarding", markup=False)


def _setup_games(tmp_path, monkeypatch, slugs: tuple[str, ...]) -> tuple[str, ...]:
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    for slug in slugs:
        game_files.new_game_from_templates(slug)
    return slugs


class _Host(App):
    def __init__(self, screen: Screen) -> None:
        super().__init__()
        self._screen = screen

    def get_default_screen(self) -> Screen:
        # Use get_default_screen() so app.query_one() resolves against the
        # SplashScreen (Textual 8.2.7 sets _compose_screen = default_screen,
        # and app.query* searches from there, not from pushed screens).
        return self._screen

    def on_mount(self) -> None:
        # Textual 8.2.7: switch_screen calls _pop_result_callback() on the outgoing
        # screen. Prime the default screen with a null callback so that works.
        if not self.screen._result_callbacks:
            self.screen._push_result_callback(self, None)


# --- list_games ---

async def test_list_games_returns_sorted_names(tmp_path, monkeypatch):
    _setup_games(tmp_path, monkeypatch, ("zebra", "alpha"))
    screen = SplashScreen(_onboarding_cls=_FakeOnboardingScreen)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert screen.list_games() == ["alpha", "zebra"]


async def test_list_games_excludes_stray_non_game_dirs(tmp_path, monkeypatch):
    """A6: directories that lack character.md or state.md are excluded."""
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    # A real game directory (both required files present).
    game_files.new_game_from_templates("realgame")
    # A stray directory with no game files.
    stray = tmp_path / "stray-dir"
    stray.mkdir()
    # A directory with only character.md (missing state.md).
    partial = tmp_path / "partial-game"
    partial.mkdir()
    (partial / "character.md").write_text("# Character\n")

    screen = SplashScreen(_onboarding_cls=_FakeOnboardingScreen)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert screen.list_games() == ["realgame"]


async def test_list_games_empty_when_no_games(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    screen = SplashScreen(_onboarding_cls=_FakeOnboardingScreen)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert screen.list_games() == []


# --- new game action ---

async def test_action_new_game_switches_to_onboarding_screen(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    screen = SplashScreen(_onboarding_cls=_FakeOnboardingScreen)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen.action_new_game()
        await pilot.pause()
        assert isinstance(app.screen, _FakeOnboardingScreen)


# --- load game action ---

async def test_action_load_game_switches_to_load_game_screen(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    screen = SplashScreen(_onboarding_cls=_FakeOnboardingScreen)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen.action_load_game()
        await pilot.pause()
        assert isinstance(app.screen, LoadGameScreen)


# --- settings action ---

async def test_action_settings_pushes_settings_screen(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    screen = SplashScreen(
        settings=default_settings(), _onboarding_cls=_FakeOnboardingScreen
    )
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen.action_settings()
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)


# --- rendered content ---

async def test_splash_art_and_greeting_rendered(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    from app.persona import SPLASH_ART, SPLASH_GREETING

    screen = SplashScreen(_onboarding_cls=_FakeOnboardingScreen)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#splash-art", Static).content == SPLASH_ART
        assert app.query_one("#splash-greeting", Static).content == SPLASH_GREETING


async def test_splash_art_block_right_aligned_but_text_left(tmp_path, monkeypatch):
    """Regression: the ASCII frog keeps its shape. The art text stays LEFT-aligned
    (per-line text-align:right staggers the varying-width lines and breaks it);
    the whole block is pushed right by the wrapper row's align-horizontal."""
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    screen = SplashScreen(_onboarding_cls=_FakeOnboardingScreen)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#splash-art", Static).styles.text_align == "left"
        assert app.query_one("#splash-art-row").styles.align_horizontal == "right"


# --- button presence in compose ---

async def test_splash_has_four_fixed_buttons_and_no_game_slug_buttons(tmp_path, monkeypatch):
    """Splash always shows exactly: btn-new, btn-load, btn-settings, btn-quit.
    Per-game slug buttons (game-<slug>) must NOT appear on the splash screen."""
    _setup_games(tmp_path, monkeypatch, ("game1", "game2"))
    screen = SplashScreen(_onboarding_cls=_FakeOnboardingScreen)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        button_ids = {b.id for b in app.query(Button)}
        assert "btn-new" in button_ids
        assert "btn-load" in button_ids
        assert "btn-settings" in button_ids
        assert "btn-quit" in button_ids
        # Per-game buttons must NOT appear on the splash screen.
        assert "game-game1" not in button_ids
        assert "game-game2" not in button_ids


# --- B7: quit action ---

async def test_action_quit_exits_app(tmp_path, monkeypatch):
    """B7: action_quit must call app.exit() and terminate the application."""
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    screen = SplashScreen(_onboarding_cls=_FakeOnboardingScreen)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen.action_quit()
        await pilot.pause()
    # After the context manager closes, the app must not be running.
    assert not app.is_running
