"""The single engine seam the TUI drives.

`make_default_runner` returns a `run(session, player_input, *, on_phase, on_chunk)`
that runs one turn through `orchestrator.play_turn`, reporting phase transitions
via `on_phase` and streamed narration chunks via `on_chunk`. The engine is
untouched: phases/chunks are surfaced by wrapping the injected dependencies.
Pure Python (no Textual) so it is unit-testable without a UI.
"""
from __future__ import annotations

from typing import Callable, Iterator

from app import narrator, orchestrator, persona, referee, scribe
from app.orchestrator import Session

OnPhase = Callable[[str], None]
OnChunk = Callable[[str], None]
TurnRunner = Callable[..., str]

# Phase keys in the order play_turn invokes them. 'dice' fires only on
# uncertain verdicts (resolve_dice is skipped otherwise).
PHASES = ("judge", "dice", "narrate", "record")


def make_default_runner(
    *,
    settings=None,
    adjudicate=referee.adjudicate,
    resolve_dice=referee.resolve_dice,
    narrate=narrator.narrate,
    record=scribe.record,
    compress_log=scribe.compress_log,
    play_turn=orchestrator.play_turn,
) -> TurnRunner:
    def run(session: Session, player_input: str, *,
            on_phase: OnPhase, on_chunk: OnChunk) -> str:
        # Roles/length are read from the shared mutable `settings` at call time,
        # so edits in the Settings screen take effect on the next turn.
        def adjudicate_w(*args):
            on_phase("judge")
            kw = {"role": settings.referee} if settings else {}
            return adjudicate(*args, **kw)

        def resolve_dice_w(verdict):
            on_phase("dice")
            return resolve_dice(verdict)

        # NOTE: generator body runs on first iteration (play_turn consumes via "".join), not at call time.
        def narrate_w(req) -> Iterator[str]:
            on_phase("narrate")
            if settings:
                kw = {"role": settings.narrator, "length": settings.narration_length}
                if settings.frog_tone == "always":
                    kw["frog_system"] = persona.FROG_SYSTEM
            else:
                kw = {}
            for chunk in narrate(req, **kw):
                on_chunk(chunk)
                yield chunk

        def record_w(*args):
            on_phase("record")
            kw = {"role": settings.scribe} if settings else {}
            return record(*args, **kw)

        def compress_w(game, **kwargs):
            if settings:
                kwargs.setdefault("role", settings.scribe)
            return compress_log(game, **kwargs)

        return play_turn(
            session, player_input,
            adjudicate=adjudicate_w, resolve_dice=resolve_dice_w,
            narrate=narrate_w, record=record_w, compress_log=compress_w,
        )

    return run
