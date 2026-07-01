"""SplashScreen — entry point: ASCII art, main menu (new / load / settings / quit)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

from app import config
from app.persona import SPLASH_ART, SPLASH_GREETING
from app.settings import Settings, default_settings
from app.tui.screens.settings import SettingsScreen


class SplashScreen(Screen):
    """Initial menu: shows art and offers new game / load game / settings / quit."""

    BINDINGS = [Binding("ctrl+q", "quit", "나가기", show=True)]

    DEFAULT_CSS = """
    SplashScreen #splash-scroll { padding: 1 2; }
    /* Right-align the WHOLE art block, but keep its text left-aligned so the
       ASCII frog's columns stay intact (per-line text-align:right breaks it). */
    SplashScreen #splash-art-row { width: 1fr; height: auto; align-horizontal: right; }
    SplashScreen #splash-art { width: auto; height: auto; text-align: left; color: $accent; }
    SplashScreen #splash-greeting { width: 1fr; text-align: right; color: $text; padding: 1 0; }
    SplashScreen Button { width: 32; margin-top: 1; }
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        _onboarding_cls=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._settings = settings or default_settings()
        # Stored as-is; resolved lazily in _get_onboarding_cls() so tests may
        # inject a fake class while production code imports the real module only
        # when the action fires, avoiding any import-order issues.
        self._onboarding_cls = _onboarding_cls

    def _get_onboarding_cls(self):
        if self._onboarding_cls is not None:
            return self._onboarding_cls
        from app.tui.screens.onboarding import OnboardingScreen  # noqa: PLC0415
        return OnboardingScreen

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="splash-scroll"):
            with Horizontal(id="splash-art-row"):
                yield Static(SPLASH_ART, id="splash-art", markup=False)
            yield Static(SPLASH_GREETING, id="splash-greeting", markup=False)
            yield Button("새 게임", id="btn-new", variant="success")
            yield Button("기존 게임", id="btn-load", variant="primary")
            yield Button("설정", id="btn-settings", variant="default")
            yield Button("나가기", id="btn-quit", variant="error")
        yield Footer()

    # ------------------------------------------------------------------
    # Query helper
    # ------------------------------------------------------------------

    def list_games(self) -> list[str]:
        """Return sorted names of real game folders currently under config.GAMES_DIR.

        A folder is a real game if it contains both character.md and state.md.
        Stray directories (e.g. partial scaffolds, editor temp dirs) are excluded.
        """
        if not config.GAMES_DIR.exists():
            return []
        return sorted(
            d.name
            for d in config.GAMES_DIR.iterdir()
            if d.is_dir()
            and (d / "character.md").exists()
            and (d / "state.md").exists()
        )

    # ------------------------------------------------------------------
    # Button dispatch
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-new":
            self.action_new_game()
        elif btn_id == "btn-load":
            self.action_load_game()
        elif btn_id == "btn-settings":
            self.action_settings()
        elif btn_id == "btn-quit":
            self.action_quit()

    # ------------------------------------------------------------------
    # Actions — callable directly in tests for determinism
    # ------------------------------------------------------------------

    def action_new_game(self) -> None:
        """Switch to the OnboardingScreen to create a new character and world."""
        cls = self._get_onboarding_cls()
        self.app.switch_screen(cls(settings=self._settings))

    def action_load_game(self) -> None:
        """Switch to the LoadGameScreen to pick a saved game."""
        from app.tui.screens.load_game import LoadGameScreen  # noqa: PLC0415
        self.app.switch_screen(LoadGameScreen(settings=self._settings))

    def action_settings(self) -> None:
        """Push the SettingsScreen (overlay — returns to whatever opened it)."""
        self.app.push_screen(SettingsScreen(self._settings))

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()
