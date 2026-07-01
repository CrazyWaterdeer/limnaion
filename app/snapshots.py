"""Per-game turn snapshots for Ctrl+Z undo.

Before each turn runs, snapshot_turn() copies the mutable game files into
games/<slug>/.snapshots/<NNNN>/ (zero-padded, monotonically increasing), keeping
only the newest config.UNDO_SNAPSHOTS. undo restores + consumes the latest.
Model output is non-deterministic, so a turn cannot be replayed — only restored.
Pure file logic: no model or Textual dependency.
"""
from __future__ import annotations

import sys
from pathlib import Path

from app import config
from app.game_files import read_text, write_text_atomic

# The mutable per-game files a turn can change. rules.md is static (excluded).
# transcript.jsonl may be absent on the very first turn and is skipped when missing.
SNAPSHOT_FILES = ("state.md", "world.md", "log.md", "character.md", "transcript.jsonl")


def _snap_root(slug: str) -> Path:
    return config.game_dir(slug) / ".snapshots"


def _snap_dirs(slug: str) -> list[Path]:
    """Existing snapshot dirs, oldest-first. Sorted NUMERICALLY (not by name) so the
    zero-pad width never matters — a 5-digit seq (10000) still orders after 9999."""
    root = _snap_root(slug)
    if not root.exists():
        return []
    numeric = (d for d in root.iterdir() if d.is_dir() and d.name.isdigit())
    return sorted(numeric, key=lambda p: int(p.name))


def snapshot_turn(slug: str) -> None:
    """Copy the current mutable game files into a fresh .snapshots/<next-seq>/ dir,
    then prune to the newest config.UNDO_SNAPSHOTS. Missing files are skipped.
    Never raises into the caller — a failed snapshot only means that one turn
    cannot be undone."""
    try:
        game = config.game_dir(slug)
        existing = _snap_dirs(slug)
        next_seq = (int(existing[-1].name) + 1) if existing else 0
        dest = _snap_root(slug) / f"{next_seq:04d}"
        dest.mkdir(parents=True, exist_ok=True)
        for name in SNAPSHOT_FILES:
            src = game / name
            if src.exists():
                write_text_atomic(dest / name, read_text(src))
        # prune oldest beyond the retention limit
        keep = config.UNDO_SNAPSHOTS
        for old in _snap_dirs(slug)[:-keep] if keep > 0 else _snap_dirs(slug):
            _rmtree(old)
    except Exception as exc:  # noqa: BLE001 - snapshotting must never break a turn
        print(f"[warn] snapshot_turn failed for {slug!r}: {exc}", file=sys.stderr)


def undo_available(slug: str) -> bool:
    """True if at least one snapshot exists to restore."""
    return bool(_snap_dirs(slug))


def restore_latest(slug: str) -> bool:
    """Make the live SNAPSHOT_FILES match the newest snapshot exactly: restore each
    file present in the snapshot (atomic), and delete any live file that the snapshot
    did not contain (so a file created during the undone turn — e.g. transcript.jsonl
    on the first turn — is truly rolled back). Delete the consumed snapshot dir and
    return True. Return False if no snapshot existed."""
    dirs = _snap_dirs(slug)
    if not dirs:
        return False
    latest = dirs[-1]
    game = config.game_dir(slug)
    for name in SNAPSHOT_FILES:
        src = latest / name
        dst = game / name
        if src.exists():
            write_text_atomic(dst, read_text(src))
        elif dst.exists():
            dst.unlink()   # absent in the snapshot -> did not exist pre-turn
    _rmtree(latest)
    return True


def _rmtree(path: Path) -> None:
    import shutil
    shutil.rmtree(path, ignore_errors=True)
