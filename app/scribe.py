"""Bookkeeping layer for a resolved turn.

`record` turns ONE resolved turn into file updates (the scribe); `compress_log`
folds an overlong log into a RECAP block (the archivist). English only — these
maintain the mechanical GM-screen truth, never narration.
"""

from __future__ import annotations

import json
from typing import Optional

from app import config, providers
from app.types import DiceResult, GameFiles, RoleConfig, StateUpdate

SCRIBE_SYSTEM = """You are the SCRIBE for a text TRPG. You do bookkeeping only; you never invent story.

You receive the game's current state.md, log.md, and world.md, plus ONE resolved turn: the
player's input, the narrated outcome, and the dice result when a roll happened. Update the books.

Reply with ONE JSON object, English only, terse and factual, with EXACTLY these keys:
- "new_state_md": the FULL rewritten state.md reflecting the new now (Scene, Location, Time,
  Condition/HP behind the screen, Resources, Inventory, Active Objectives, Status Effects,
  Last turn #). Keep the template's headings. Keep exact HP and mechanical truth here.
- "log_entry": ONE line for log.md, exactly in the form
  "Turn N; Action: <attempted>; Roll: <mode + band, or 'no roll'>; Outcome: <factual>; Changes: <state/world deltas>".
- "world_additions": markdown to APPEND to world.md for genuinely NEW canonical facts / NPCs /
  locations only; use the empty string "" when nothing is new. Never repeat what world.md holds.
- "new_compact_state": a clinical one-paragraph snapshot for the next turn's context — who, where,
  what is at stake, standing threats. No narration, no flourish, no Korean.

Keep the exact mechanical truth (HP, totals, bands) in the files; they are the GM screen.
Output the JSON object only — no prose, no Korean, no embellishment."""


def _extract_json(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"no JSON object in scribe output: {raw!r}")
    return json.loads(raw[start : end + 1])


def parse_state_update(raw: str) -> StateUpdate:
    data = _extract_json(raw)
    return StateUpdate(
        new_state_md=data["new_state_md"],
        log_entry=data["log_entry"],
        world_additions=data.get("world_additions", ""),
        new_compact_state=data["new_compact_state"],
    )


def _dice_line(dice: Optional[DiceResult]) -> str:
    if dice is None:
        return "Roll: no roll"
    if dice.picked_option is not None:
        return f"Oracle: picked option {dice.picked_index} -> {dice.picked_option}"
    return f"Roll: band={dice.band}, total={dice.total}"


def record(
    game: GameFiles,
    player_input: str,
    narration: str,
    dice: Optional[DiceResult],
    *,
    role: RoleConfig = config.SCRIBE,
    complete=providers.complete,
) -> StateUpdate:
    prompt = (
        "## state.md (current)\n" + game.state + "\n\n"
        "## log.md (current)\n" + game.log + "\n\n"
        "## world.md (current)\n" + game.world + "\n\n"
        "## Resolved turn\n"
        "Player input: " + player_input + "\n"
        "Narrated outcome: " + narration + "\n"
        + _dice_line(dice) + "\n"
    )
    raw = complete(role, SCRIBE_SYSTEM, prompt, json_out=True)
    return parse_state_update(raw)


ARCHIVIST_SYSTEM = """You are the ARCHIVIST for a text TRPG: context hygiene, never story.

Compress an overlong log.md without losing anything that still matters. Summarize all but the
most recent kept-verbatim turns into a single "## RECAP (Turns A-B)" block. Preserve decisions
with lasting consequences, promises/threats made, items gained or lost, relationships changed,
locations discovered, and unresolved threads; drop moment-to-moment flavor and inconsequential
failed attempts. Keep any existing RECAP blocks (you may merge adjacent ones) and keep the most
recent turns verbatim.

Output the FULL new log.md text only — English, terse, no commentary, no Korean."""


def compress_log(
    game: GameFiles,
    *,
    keep_n: int = 10,
    role: RoleConfig = config.SCRIBE,
    complete=providers.complete,
) -> str:
    prompt = (
        f"Keep the most recent {keep_n} turns verbatim; recap everything older.\n\n"
        "## log.md (current)\n" + game.log + "\n"
    )
    return complete(role, ARCHIVIST_SYSTEM, prompt, json_out=False)
