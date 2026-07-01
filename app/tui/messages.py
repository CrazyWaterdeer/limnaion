"""Thread-safe messages posted from the turn worker to the UI thread."""
from __future__ import annotations

from textual.message import Message


class PhaseChanged(Message):
    """A turn phase began: 'judge' | 'dice' | 'narrate' | 'record' | 'idle'."""

    def __init__(self, phase: str) -> None:
        self.phase = phase
        super().__init__()


class NarrationChunk(Message):
    """A streamed narration delta for the current turn."""

    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()


class TurnComplete(Message):
    """The turn finished; `text` is the full narration as recorded."""

    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()


class TurnFailed(Message):
    """The turn raised; `error` is a short message for the player."""

    def __init__(self, error: str) -> None:
        self.error = error
        super().__init__()


class EpilogueReady(Message):
    """The epilogue body finished composing; `body` is the closing prose."""

    def __init__(self, body: str) -> None:
        self.body = body
        super().__init__()


class EpilogueFailed(Message):
    """Composing the epilogue body raised; `error` is a short message."""

    def __init__(self, error: str) -> None:
        self.error = error
        super().__init__()
