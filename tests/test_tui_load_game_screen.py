"""Tests for LoadGameScreen: game list, button rendering, navigation, delete."""
from __future__ import annotations

from textual.app import App
from textual.screen import Screen
from textual.widgets import Button, Static

from app import config, game_files
from app.tui.screens.load_game import LoadGameScreen
from app.tui.screens.play import PlayScreen
from app.tui.screens.splash import SplashScreen


def _setup_games_with_templates(tmp_path, monkeypatch, slugs):
    """Set up games using a tmp GAMES_DIR with inline templates (no real templates needed)."""
    games_dir = tmp_path / "games"
    games_dir.mkdir()
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    for name in game_files.GAME_FILE_NAMES:
        (tpl_dir / name).write_text(f"TEMPLATE {name}\n", encoding="utf-8")
    engine = tmp_path / "engine.md"
    engine.write_text("ENGINE\n", encoding="utf-8")
    monkeypatch.setattr(config, "GAMES_DIR", games_dir)
    monkeypatch.setattr(config, "TEMPLATES_DIR", tpl_dir)
    monkeypatch.setattr(config, "ENGINE_MD", engine)
    for slug in slugs:
        game_files.new_game_from_templates(slug)
    return games_dir


class _Host(App):
    def __init__(self, screen: Screen) -> None:
        super().__init__()
        self._screen = screen

    def get_default_screen(self) -> Screen:
        return self._screen

    def on_mount(self) -> None:
        # Textual 8.2.7: switch_screen calls _pop_result_callback() on the outgoing
        # screen. Prime the default screen with a null callback so that works.
        if not self.screen._result_callbacks:
            self.screen._push_result_callback(self, None)


def _setup_games(tmp_path, monkeypatch, slugs: tuple[str, ...]) -> tuple[str, ...]:
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    for slug in slugs:
        game_files.new_game_from_templates(slug)
    return slugs


# --- list_games ---

async def test_list_games_returns_scaffolded_games(tmp_path, monkeypatch):
    _setup_games(tmp_path, monkeypatch, ("alpha", "zebra"))
    screen = LoadGameScreen()
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert screen.list_games() == ["alpha", "zebra"]


async def test_list_games_empty_when_no_games(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    screen = LoadGameScreen()
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert screen.list_games() == []


# --- button rendering ---

async def test_game_buttons_rendered_for_each_game(tmp_path, monkeypatch):
    _setup_games(tmp_path, monkeypatch, ("hero", "rogue"))
    screen = LoadGameScreen()
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        button_ids = {b.id for b in app.query(Button)}
        assert "game-hero" in button_ids
        assert "game-rogue" in button_ids


async def test_play_button_shows_title_not_slug(tmp_path, monkeypatch):
    """The play button label is the game's world.md title (the evocative name the
    creator wrote), not the internal folder slug like 'game-2'."""
    _setup_games(tmp_path, monkeypatch, ("game-2",))
    (config.GAMES_DIR / "game-2" / "world.md").write_text(
        "# 철문 너머의 빚\n\n## Setting\n안개 낀 부두.", encoding="utf-8"
    )
    screen = LoadGameScreen()
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        btn = app.query_one("#game-game-2", Button)
        assert str(btn.label) == "철문 너머의 빚"  # title, not the slug "game-2"


async def test_empty_note_shown_when_no_games(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    screen = LoadGameScreen()
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        statics = [s.content for s in app.query(Static)]
        assert any("저장된 항해가 없네" in c for c in statics)


# --- select game ---

async def test_selecting_game_button_switches_to_play_screen(tmp_path, monkeypatch):
    _setup_games(tmp_path, monkeypatch, ("mygame",))
    screen = LoadGameScreen()
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Trigger the button-press handler directly for determinism.
        btn = app.query_one("#game-mygame", Button)
        screen.on_button_pressed(Button.Pressed(btn))
        await pilot.pause()
        assert isinstance(app.screen, PlayScreen)
        assert app.screen.session.slug == "mygame"


# --- back action ---

async def test_action_back_switches_to_splash_screen(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    screen = LoadGameScreen()
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen.action_back()
        await pilot.pause()
        assert isinstance(app.screen, SplashScreen)


# --- delete game ---

async def test_confirm_delete_removes_dir_and_row(tmp_path, monkeypatch):
    """Confirming delete removes the game dir and the row widget; the other game survives."""
    _setup_games_with_templates(tmp_path, monkeypatch, ("keep", "gone"))
    screen = LoadGameScreen()
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Simulate a confirmed deletion by calling the callback directly.
        screen._on_confirm_delete("gone")
        await pilot.pause()
        # The game directory must be deleted.
        assert not config.game_dir("gone").exists()
        # The row widget for "gone" must be removed from the screen.
        assert len(screen.query("#row-gone")) == 0
        # The other game's row must still be present.
        assert len(screen.query("#row-keep")) == 1
        assert config.game_dir("keep").exists()


async def test_cancel_delete_leaves_game_intact(tmp_path, monkeypatch):
    """Cancelling the delete modal leaves the game dir and row untouched."""
    _setup_games_with_templates(tmp_path, monkeypatch, ("survivor",))
    screen = LoadGameScreen()
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Simulate cancellation (result=None).
        screen._on_confirm_delete(None)
        await pilot.pause()
        # Directory must still exist.
        assert config.game_dir("survivor").exists()
        # Row widget must still be present.
        assert len(screen.query("#row-survivor")) == 1
