"""Snapshot/restore/prune for turn undo — pure file logic, tmp GAMES_DIR."""
from __future__ import annotations

from pathlib import Path

import pytest

from app import config, snapshots


def _write(d: Path, name: str, text: str) -> None:
    (d / name).write_text(text, encoding="utf-8")


@pytest.fixture
def game(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    d = config.game_dir("g")
    d.mkdir(parents=True)
    _write(d, "state.md", "state-0")
    _write(d, "world.md", "world-0")
    _write(d, "log.md", "log-0")
    _write(d, "character.md", "char-0")
    _write(d, "transcript.jsonl", '{"p":"","n":"opening"}\n')
    return d


def test_snapshot_then_restore_round_trips_all_files(game):
    snapshots.snapshot_turn("g")           # capture the -0 state
    # simulate a turn mutating every file
    for name in ("state.md", "world.md", "log.md", "character.md"):
        (game / name).write_text("MUTATED", encoding="utf-8")
    (game / "transcript.jsonl").write_text('{"p":"","n":"opening"}\n{"p":"x","n":"y"}\n', encoding="utf-8")

    assert snapshots.undo_available("g") is True
    assert snapshots.restore_latest("g") is True

    assert (game / "state.md").read_text(encoding="utf-8") == "state-0"
    assert (game / "world.md").read_text(encoding="utf-8") == "world-0"
    assert (game / "log.md").read_text(encoding="utf-8") == "log-0"
    assert (game / "character.md").read_text(encoding="utf-8") == "char-0"
    assert (game / "transcript.jsonl").read_text(encoding="utf-8") == '{"p":"","n":"opening"}\n'


def test_restore_consumes_snapshot_so_undo_steps_back(game):
    snapshots.snapshot_turn("g")                                   # snap A (state-0)
    (game / "state.md").write_text("state-1", encoding="utf-8")
    snapshots.snapshot_turn("g")                                   # snap B (state-1)
    (game / "state.md").write_text("state-2", encoding="utf-8")

    assert snapshots.restore_latest("g") is True                   # -> state-1
    assert (game / "state.md").read_text(encoding="utf-8") == "state-1"
    assert snapshots.restore_latest("g") is True                   # -> state-0
    assert (game / "state.md").read_text(encoding="utf-8") == "state-0"
    assert snapshots.undo_available("g") is False
    assert snapshots.restore_latest("g") is False                  # nothing left


def test_prune_keeps_only_newest_N(game, monkeypatch):
    monkeypatch.setattr(config, "UNDO_SNAPSHOTS", 3)
    for i in range(5):
        (game / "state.md").write_text(f"state-{i}", encoding="utf-8")
        snapshots.snapshot_turn("g")
    snap_root = game / ".snapshots"
    assert len(list(snap_root.iterdir())) == 3                     # only newest 3 kept
    # the newest snapshot holds state-4 (the last captured)
    assert snapshots.restore_latest("g") is True
    assert (game / "state.md").read_text(encoding="utf-8") == "state-4"


def test_missing_transcript_is_skipped(game):
    (game / "transcript.jsonl").unlink()                           # first turn: no transcript yet
    snapshots.snapshot_turn("g")                                   # must not raise
    (game / "state.md").write_text("MUT", encoding="utf-8")
    assert snapshots.restore_latest("g") is True
    assert (game / "state.md").read_text(encoding="utf-8") == "state-0"
    assert not (game / "transcript.jsonl").exists()                # stays absent, no crash


def test_undo_deletes_file_created_during_turn(game):
    (game / "transcript.jsonl").unlink()                           # pre-turn: no transcript
    snapshots.snapshot_turn("g")                                   # snapshot without transcript
    # the turn creates transcript.jsonl (as the play screen does on turn 1)
    (game / "transcript.jsonl").write_text('{"p":"x","n":"y"}\n', encoding="utf-8")
    assert snapshots.restore_latest("g") is True
    # symmetric rollback: a file absent in the snapshot is removed on restore
    assert not (game / "transcript.jsonl").exists()


def test_no_snapshots_dir_is_safe(game):
    assert snapshots.undo_available("g") is False
    assert snapshots.restore_latest("g") is False
