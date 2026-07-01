"""Growing, soft-wrapping player input.

A multi-line input that wraps long text and grows in height (capped, then
scrolls) instead of scrolling a single line horizontally. Built on TextArea but
preserves the old single-line GameInput surface so the play screen is unchanged:
Enter submits (emits ``Submitted`` → ``on_input_submitted``), ``.value`` gets/sets
the text, ``remember()`` + ↑/↓ walk submission history. ctrl+j inserts a literal
newline.
"""
from __future__ import annotations

from textual import events
from textual.message import Message
from textual.widgets import TextArea


class GameInput(TextArea):
    """Soft-wrapping, auto-growing player input with Enter-submit and ↑/↓ history."""

    DEFAULT_CSS = """
    GameInput {
        height: auto;
        max-height: 8;
        background: $surface;
    }
    """

    class Submitted(Message, namespace="input"):
        """Enter-submit. ``namespace="input"`` routes it to ``on_input_submitted``
        and ``.value`` mirrors ``Input.Submitted`` so the screen handler is unchanged."""

        def __init__(self, input: "GameInput", value: str) -> None:
            self.input = input
            self.value = value
            super().__init__()

        @property
        def control(self) -> "GameInput":
            return self.input

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("soft_wrap", True)
        kwargs.setdefault("compact", True)
        kwargs.setdefault("placeholder", '*행동*, "대사", 또는 (ooc) 메모…')
        super().__init__(**kwargs)
        self._history: list[str] = []
        self._hpos: int | None = None  # None = live edit; else index into history

    # --- Input-compatible value API (the screen + tests use .value) ---
    @property
    def value(self) -> str:
        return self.text

    @value.setter
    def value(self, text: str) -> None:
        self.text = text or ""
        self.move_cursor(self.document.end)

    # --- submission history (↑/↓) ---
    def remember(self, text: str) -> None:
        if text and (not self._history or self._history[-1] != text):
            self._history.append(text)
        self._hpos = None

    def _show(self, idx: int | None) -> None:
        self._hpos = idx
        self.value = "" if idx is None else self._history[idx]

    def action_history_prev(self) -> None:
        if not self._history:
            return
        if self._hpos is None:
            self._show(len(self._history) - 1)
        elif self._hpos > 0:
            self._show(self._hpos - 1)

    def action_history_next(self) -> None:
        if self._hpos is None:
            return
        if self._hpos < len(self._history) - 1:
            self._show(self._hpos + 1)
        else:
            self._show(None)

    # --- keys: Enter submits, ctrl+j newline, ↑/↓ history while single-line ---
    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            self.post_message(self.Submitted(self, self.text))
            return
        if event.key == "ctrl+j":
            event.prevent_default()
            event.stop()
            self.insert("\n")
            return
        # History only when the text is a single document line, so ↑/↓ still move
        # the cursor once the player has inserted explicit newlines.
        if event.key in ("up", "down") and "\n" not in self.text:
            event.prevent_default()
            event.stop()
            if event.key == "up":
                self.action_history_prev()
            else:
                self.action_history_next()
            return
        await super()._on_key(event)
