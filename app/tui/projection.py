"""Pure projections from game files to player-safe status text.

House rule: never show the player raw numbers (HP values, attribute modifiers,
the HP formula). These helpers parse state.md / character.md and emit only
worded, player-safe views. No Textual imports — pure, unit-tested in isolation.
"""
from __future__ import annotations

import re

from app.types import GameFiles

_H1_RE = re.compile(r"^#\s+(.*)$", re.MULTILINE)
_TURN_RE = re.compile(r"\*\*Last turn #:\*\*\s*(\d+)")
_FIELD_RE = re.compile(r"^- \*\*(?P<key>[^:*]+):\*\*\s*(?P<val>.*)$")
_OBJ_RE = re.compile(r"^\s*- \[(?P<mark>[ xX])\]\s*(?P<text>.*)$")
_HP_RE = re.compile(r"HP\s*(\d+)\s*/\s*(\d+)", re.IGNORECASE)


def game_title(game: GameFiles) -> str:
    """world.md H1 with a leading 'World:' stripped; falls back to the slug."""
    m = _H1_RE.search(game.world)
    if m:
        title = re.sub(r"^World:\s*", "", m.group(1).strip()).strip()
        if title:
            return title
    return game.slug


def turn_number(game: GameFiles) -> int:
    """Last recorded turn number from state.md ('- **Last turn #:** N'); 0 if absent."""
    m = _TURN_RE.search(game.state)
    return int(m.group(1)) if m else 0


def parse_state_fields(state_md: str) -> dict[str, str]:
    """Map each '- **Key:** value' line to {key: value} (sub-lists excluded)."""
    out: dict[str, str] = {}
    for line in state_md.splitlines():
        m = _FIELD_RE.match(line.strip())
        if m:
            out[m.group("key").strip()] = m.group("val").strip()
    return out


def parse_objectives(state_md: str) -> list[tuple[bool, str]]:
    """(done, text) for each '- [ ]' / '- [x]' checklist item."""
    items: list[tuple[bool, str]] = []
    for line in state_md.splitlines():
        m = _OBJ_RE.match(line)
        if m:
            items.append((m.group("mark").lower() == "x", m.group("text").strip()))
    return items


def wound_band(condition: str) -> str:
    """Convert a Condition string to a player-safe wound word ('HP 10/10' ->
    '멀쩡함'). Already-worded input passes through; all digits are stripped so
    no numbers ever reach the player (house rule)."""
    m = _HP_RE.search(condition)
    if not m:
        cleaned = re.sub(r"\bHP\b", "", condition, flags=re.IGNORECASE)
        cleaned = re.sub(r"\d+\s*/\s*\d+", "", cleaned)
        cleaned = re.sub(r"\d+", "", cleaned)          # no standalone digits to the player
        cleaned = cleaned.strip(" ()-—")
        return cleaned or "멀쩡함"
    cur, mx = int(m.group(1)), int(m.group(2))
    if mx <= 0:
        return "멀쩡함"
    if cur <= 0:
        return "빈사 상태"
    ratio = cur / mx
    if ratio >= 1.0:
        return "멀쩡함"
    if ratio >= 0.6:
        return "긁힌 상처"
    if ratio >= 0.3:
        return "부상"
    return "중상"


# state.md keys we surface, in display order. 'Condition' is reworded;
# 'Last turn #' belongs in the header, not the panel.
_STATUS_KEYS = ("Scene", "Location", "Time", "Condition", "Resources",
                "Inventory", "Status Effects")


def status_lines(game: GameFiles) -> list[str]:
    """Player-safe status-panel lines (plain text, no markup) — no raw numbers."""
    fields = parse_state_fields(game.state)
    lines: list[str] = []
    for key in _STATUS_KEYS:
        if key not in fields:
            continue
        val = wound_band(fields[key]) if key == "Condition" else fields[key]
        lines.append(f"{key}: {val}")
    objs = parse_objectives(game.state)
    if objs:
        lines.append("목표:")
        for done, text in objs:
            lines.append(f"  {'✓' if done else '○'} {text}")
    return lines


# character.md sections we may show. The hidden 'Attributes' block and the
# 'Notes' block (HP formula) are deliberately NOT whitelisted.
_CHAR_ALLOWED = ("Concept", "Specialties", "Drives & Personality",
                 "Bonds & Relationships", "Background", "Assets / Signature Gear")


def character_sections(character_md: str) -> list[tuple[str, str]]:
    """Split character.md into (heading, body) for each '## ' section."""
    sections: list[tuple[str, str]] = []
    head: str | None = None
    body: list[str] = []
    for line in character_md.splitlines():
        if line.startswith("## "):
            if head is not None:
                sections.append((head, "\n".join(body).strip()))
            head, body = line[3:].strip(), []
        elif head is not None:
            body.append(line)
    if head is not None:
        sections.append((head, "\n".join(body).strip()))
    return sections


def character_lines(game: GameFiles) -> list[str]:
    """Player-safe character sheet — flavor sections only, no hidden numbers.
    Plain text (no markup) so the panel can set markup=False safely."""
    out: list[str] = []
    for head, body in character_sections(game.character):
        if head not in _CHAR_ALLOWED:
            continue
        out.append(f"{head}")
        out.extend(bl.rstrip() for bl in body.splitlines() if bl.strip())
        out.append("")
    if out and out[-1] == "":
        out.pop()
    return out


def npc_lines(game: GameFiles) -> list[str]:
    """Player-safe cast list: the bullet entries under world.md's 'Key NPCs'
    section. GM-only sections (Lore, Open Threads, etc.) are excluded."""
    out: list[str] = []
    in_section = False
    for line in game.world.splitlines():
        if line.startswith("## "):
            in_section = line[3:].strip().lower().startswith("key npcs")
            continue
        if in_section and line.strip():
            out.append(line.rstrip())
    return out
