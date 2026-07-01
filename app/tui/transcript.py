"""Per-game transcript: persist (player input, narration) turns so a resumed game
shows where it left off and the narrator regains recent context. JSONL, one turn
per line, under games/<slug>/transcript.jsonl."""
from __future__ import annotations

import json
from pathlib import Path

from app import config


def _path(slug: str) -> Path:
    return config.game_dir(slug) / "transcript.jsonl"


def append_turn(slug: str, player_input: str, narration: str) -> None:
    p = _path(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"p": player_input, "n": narration}, ensure_ascii=False)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_recent(slug: str, n: int = 3) -> list[tuple[str, str]]:
    """The last `n` (player_input, narration) turns, oldest first. [] if none."""
    p = _path(slug)
    if not p.exists():
        return []
    out: list[tuple[str, str]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            out.append((d.get("p", ""), d.get("n", "")))
        except json.JSONDecodeError:
            continue
    return out[-n:]
