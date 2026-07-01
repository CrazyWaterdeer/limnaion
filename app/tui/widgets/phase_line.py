"""One-line phase indicator beneath the story view.

Phase B labels are plain froggy-neutral status text; Phase D swaps in the
witty marsh/Muses loading pool. The label strings stay Korean (player-facing).
"""
from __future__ import annotations

import random

from textual.reactive import reactive
from textual.widgets import Static

from app import persona

PHASE_LABELS = {
    "": "",
    "idle": "",
    "judge": "⚖  판정하는 중…",
    "dice": "🎲  주사위를 굴리는 중…",
    "narrate": "✍  서술하는 중…",
    "record": "📓  기록하는 중…",
}

# Module-level RNG used by watch_phase.  Tests monkeypatch this attribute:
#   monkeypatch.setattr(app.tui.widgets.phase_line, "_rng", fake_rng)
_rng = random


class PhaseLine(Static):
    """Displays the current turn phase as a short status line."""

    phase = reactive("")

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)

    def watch_phase(self, phase: str) -> None:
        # Ask persona for a witty pool line; fall back to the static label when
        # the pool is empty (pick_loading_line returns "") or the phase is unknown.
        line = persona.pick_loading_line(phase, rng=_rng)
        if not line:
            line = PHASE_LABELS.get(phase, "")
        self.update(line)

    def set_phase(self, phase: str) -> None:
        self.phase = phase
