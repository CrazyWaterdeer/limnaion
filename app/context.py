"""Per-turn context assembly.

Layer 3 (narrator, Gemini) sees recent raw narration via NarrationRequest.
Layer 1 (referee, Claude) MUST NOT see recent raw narration — referee_context
omits it by construction (it does not even accept a RecentTurns).
"""
from __future__ import annotations

from typing import Optional

from app import config
from app.types import NarrationRequest


class RecentTurns:
    """Ring buffer of the most recent player/narration exchanges (verbatim, capped at k)."""

    def __init__(self, k: int = config.RECENT_TURNS_K) -> None:
        self.k = k
        self._turns: list[tuple[str, str]] = []

    def add(self, player_input: str, narration: str) -> None:
        self._turns.append((player_input, narration))
        if len(self._turns) > self.k:
            self._turns = self._turns[-self.k:]

    def as_list(self) -> list[str]:
        # verbatim exchanges, newest last
        return [
            f"PLAYER: {player_input}\nGM: {narration}"
            for player_input, narration in self._turns
        ]


def build_narration_request(
    narration_rules: str,
    recent: RecentTurns,
    compact_state: str,
    player_input: str,
    committed_outcome: Optional[str],
    visibility: str,
) -> NarrationRequest:
    return NarrationRequest(
        narration_rules=narration_rules,
        recent_turns_raw=recent.as_list(),
        compact_state=compact_state,
        player_input=player_input,
        committed_outcome=committed_outcome,
        visibility=visibility,
    )


def referee_context(
    referee_rules: str,
    character_md: str,
    compact_state: str,
    player_input: str,
) -> str:
    # No recent raw narration here — layer-1 adjudication bypasses the narrator.
    return (
        f"{referee_rules}\n\n"
        f"## Character\n{character_md}\n\n"
        f"## Current State\n{compact_state}\n\n"
        f"## Player Input\n{player_input}"
    )
