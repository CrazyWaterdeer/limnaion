"""Collapsible status panel: live player-safe state + character and NPC subviews."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from app.tui import projection
from app.types import GameFiles

# View cycle order: state → character → npc → state → …
_VIEWS = ("state", "character", "npc")


class StatusPanel(VerticalScroll):
    """Player-safe status (no numbers). The screen toggles the `-hidden` class
    (Tab); `cycle_view()` advances state → character → npc → state.
    Call `refresh_from(game)` after each turn."""

    DEFAULT_CSS = """
    StatusPanel { width: 34; border-left: solid $panel; padding: 0 1; }
    StatusPanel.-hidden { display: none; }
    StatusPanel #status-title { text-style: bold; color: $accent; margin-bottom: 1; }
    """

    def __init__(self, game: GameFiles, **kwargs) -> None:
        super().__init__(**kwargs)
        self._game = game
        self._mode = "state"  # one of: "state", "character", "npc"

    def compose(self) -> ComposeResult:
        yield Static("", id="status-title", markup=False)
        yield Static("", id="status-body", markup=False)

    def on_mount(self) -> None:
        self._update_display()

    def refresh_from(self, game: GameFiles) -> None:
        self._game = game
        self._update_display()

    def cycle_view(self) -> None:
        """Advance the view: state → character → npc → state → …"""
        idx = _VIEWS.index(self._mode)
        self._mode = _VIEWS[(idx + 1) % len(_VIEWS)]
        self._update_display()

    def toggle_character(self) -> None:
        """Alias for cycle_view() — kept for backward compatibility."""
        self.cycle_view()

    def _update_display(self) -> None:
        """Push current game/mode state into the child Static widgets.

        Named _update_display (not _render) to avoid shadowing Widget._render(),
        which Textual calls internally and expects to return a Visual object.
        """
        if self._mode == "state":
            title = projection.game_title(self._game)
            lines = projection.status_lines(self._game)
        elif self._mode == "character":
            title = "캐릭터"
            lines = projection.character_lines(self._game)
        else:  # npc
            title = "등장인물"
            lines = projection.npc_lines(self._game) or ["(아직 마주친 인물이 없네)"]
        self.query_one("#status-title", Static).update(title)
        self.query_one("#status-body", Static).update("\n".join(lines))
