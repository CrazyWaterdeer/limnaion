"""The Limnaion Textual application."""
from __future__ import annotations

from textual.app import App
from textual.screen import Screen

from app.orchestrator import load_session
from app.settings import Settings, default_settings, load_settings


class LimnaionApp(App):
    TITLE = "Limnaion"

    def __init__(self, *, slug: str | None = None, settings: Settings | None = None,
                 runner=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._slug = slug
        self._settings = settings or default_settings()
        self._runner = runner

    def on_mount(self) -> None:
        # Textual 8.2.7: switch_screen calls _pop_result_callback() on the outgoing
        # screen. The default screen (loaded via get_default_screen) has no result
        # callback in its stack, which raises IndexError. Priming it with a null
        # callback allows switch_screen to work from the very first screen.
        if not self.screen._result_callbacks:
            self.screen._push_result_callback(self, None)
        if self._settings.theme in self.available_themes:
            self.theme = self._settings.theme

    def get_default_screen(self) -> Screen:
        # No slug -> the splash hub (pick or create a game). A slug -> straight into
        # play. Screen imports are lazy to avoid the play<->splash<->epilogue cycle.
        if self._slug is None:
            from app.tui.screens.splash import SplashScreen
            return SplashScreen(settings=self._settings)
        from app.tui.screens.play import PlayScreen
        return PlayScreen(load_session(self._slug), settings=self._settings,
                          runner=self._runner)


def run_play(slug: str | None = None, *, settings: Settings | None = None,
             runner=None) -> None:
    """Launch the TUI (blocking). No slug -> splash hub; a slug -> that game."""
    s = settings or load_settings()
    if s.openrouter_api_key:
        import os
        os.environ["OPENROUTER_API_KEY"] = s.openrouter_api_key
    LimnaionApp(slug=slug, settings=s, runner=runner).run()
