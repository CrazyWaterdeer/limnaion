"""Tests for app.tui.transcript — per-game JSONL transcript persistence."""
from app import config
from app.tui import transcript


def test_append_then_load_returns_both_turns_oldest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    slug = "game1"
    transcript.append_turn(slug, "문을 열어", "문이 삐걱거리며 열린다.")
    transcript.append_turn(slug, "안을 살핀다", "어둠뿐이다.")
    turns = transcript.load_recent(slug)
    assert len(turns) == 2
    assert turns[0] == ("문을 열어", "문이 삐걱거리며 열린다.")
    assert turns[1] == ("안을 살핀다", "어둠뿐이다.")


def test_load_recent_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    result = transcript.load_recent("no-such-game")
    assert result == []


def test_load_recent_n1_returns_only_last(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    slug = "game2"
    transcript.append_turn(slug, "첫 번째", "첫 번째 응답")
    transcript.append_turn(slug, "두 번째", "두 번째 응답")
    transcript.append_turn(slug, "세 번째", "세 번째 응답")
    turns = transcript.load_recent(slug, n=1)
    assert len(turns) == 1
    assert turns[0] == ("세 번째", "세 번째 응답")


def test_corrupt_line_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    slug = "game3"
    p = transcript._path(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Write a valid line, a corrupt line, and another valid line.
    p.write_text(
        '{"p": "입력1", "n": "응답1"}\n'
        'NOT VALID JSON }{{\n'
        '{"p": "입력2", "n": "응답2"}\n',
        encoding="utf-8",
    )
    turns = transcript.load_recent(slug)
    assert len(turns) == 2
    assert turns[0] == ("입력1", "응답1")
    assert turns[1] == ("입력2", "응답2")
