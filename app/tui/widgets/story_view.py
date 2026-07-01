"""Scrollable story transcript with live-streaming narration."""
from __future__ import annotations

from textual.containers import VerticalScroll
from textual.widgets import Static


class StoryView(VerticalScroll):
    """Append-only transcript: dim player echoes + live-streamed narration.

    Per turn: add_player_echo(input) -> begin_narration() -> append_narration(chunk)*
    -> end_narration(final). Narration streams into one Static updated in place;
    end_narration detaches it so the next turn starts a fresh block.
    """

    DEFAULT_CSS = """
    StoryView { padding: 1 2; }
    StoryView .echo { text-align: right; color: $accent; text-style: bold; margin-top: 1; }
    StoryView .narration { color: $text; margin-bottom: 1; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._active: Static | None = None
        self._buf = ""

    async def add_player_echo(self, text: str) -> None:
        await self.mount(Static(text, classes="echo", markup=False))
        self.scroll_end(animate=False)

    async def begin_narration(self) -> None:
        self._buf = ""
        self._active = Static("", classes="narration", markup=False)
        await self.mount(self._active)
        self.scroll_end(animate=False)

    def append_narration(self, chunk: str) -> None:
        if self._active is None:
            return
        self._buf += chunk
        self._active.update(self._buf)
        self.scroll_end(animate=False)

    def end_narration(self, final_text: str | None = None) -> None:
        if self._active is not None and final_text is not None:
            self._active.update(final_text)
        self._active = None
        self._buf = ""
        self.scroll_end(animate=False)

    async def reset(self) -> None:
        """Remove all mounted content and clear in-progress narration state, so the
        story can be rebuilt from scratch (used by turn undo to replay the restored
        transcript)."""
        self._active = None
        self._buf = ""
        await self.remove_children()

    async def show_note(self, text: str) -> None:
        """Mount a standalone note (e.g. a turn-failure message), independent of
        any in-progress narration block.

        If a narration block was begun but received no chunks (empty buffer),
        it is removed first to avoid a blank line above the failure note.
        Already-streamed prose (non-empty buffer) is preserved.
        """
        if self._active is not None and self._buf == "":
            await self._active.remove()      # drop empty placeholder; keep any streamed prose
        self._active = None
        self._buf = ""
        await self.mount(Static(text, classes="narration", markup=False))
        self.scroll_end(animate=False)

    @property
    def current_text(self) -> str:
        return self._buf
