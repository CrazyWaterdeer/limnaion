"""LoadGameScreen — pick a saved game to resume."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Footer, Static

from app import config, game_files
from app.orchestrator import load_session
from app.settings import Settings, default_settings
from app.tui import projection
from app.tui.screens.play import PlayScreen


class ConfirmDeleteScreen(ModalScreen):
    BINDINGS = [Binding("escape", "cancel", "취소")]
    DEFAULT_CSS = """
    ConfirmDeleteScreen { align: center middle; }
    ConfirmDeleteScreen #box { width: 50; height: auto; border: round $error;
        padding: 1 2; background: $panel; }
    ConfirmDeleteScreen Button { width: 1fr; margin-top: 1; }
    """

    def __init__(self, slug: str, title: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._slug = slug
        self._title = title or slug

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static(f"'{self._title}' 항해를 늪 바닥에 가라앉힐까?\n되돌릴 수 없네. 코악.", markup=False)
            yield Button("삭제", id="confirm-del", variant="error")
            yield Button("취소", id="cancel-del", variant="default")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(self._slug if event.button.id == "confirm-del" else None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class LoadGameScreen(Screen):
    BINDINGS = [Binding("escape", "back", "뒤로", show=True)]

    DEFAULT_CSS = """
    LoadGameScreen #load-title { dock: top; height: 1; background: $panel;
        color: $accent; padding: 0 1; }
    LoadGameScreen #load-list { padding: 1 2; }
    LoadGameScreen .game-row { height: auto; }
    LoadGameScreen Button { margin-bottom: 1; }
    LoadGameScreen .play-btn { width: 40; }
    LoadGameScreen .del-btn { width: 8; margin-left: 1; }
    """

    def __init__(self, *, settings: Settings | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._settings = settings or default_settings()

    def list_games(self) -> list[str]:
        if not config.GAMES_DIR.exists():
            return []
        return sorted(
            d.name for d in config.GAMES_DIR.iterdir()
            if d.is_dir() and (d / "character.md").exists() and (d / "state.md").exists()
        )

    def _title_for(self, slug: str) -> str:
        """The game's evocative title (world.md H1); falls back to the slug.

        The folder slug is an internal ASCII id; the player sees the story's title."""
        try:
            return projection.game_title(game_files.load_game(slug))
        except Exception:
            return slug

    def compose(self) -> ComposeResult:
        yield Static("기존 게임 — 건너갈 물길을 고르게", id="load-title", markup=False)
        with VerticalScroll(id="load-list"):
            games = self.list_games()
            if not games:
                yield Static("아직 저장된 항해가 없네. 코악.", markup=False)
            for slug in games:
                with Horizontal(id=f"row-{slug}", classes="game-row"):
                    yield Button(self._title_for(slug), id=f"game-{slug}",
                                 variant="default", classes="play-btn")
                    yield Button("삭제", id=f"del-{slug}", variant="error", classes="del-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid.startswith("game-"):
            slug = bid[len("game-"):]
            self.app.switch_screen(PlayScreen(load_session(slug), settings=self._settings))
        elif bid.startswith("del-"):
            slug = bid[len("del-"):]
            self.app.push_screen(
                ConfirmDeleteScreen(slug, self._title_for(slug)), self._on_confirm_delete
            )

    def _on_confirm_delete(self, result) -> None:
        if not result:
            return
        slug = result
        game_files.delete_game(slug)
        try:
            self.query_one(f"#row-{slug}").remove()
        except Exception:
            pass

    def action_back(self) -> None:
        from app.tui.screens.splash import SplashScreen  # noqa: PLC0415 (avoid import cycle)
        self.app.switch_screen(SplashScreen(settings=self._settings))
