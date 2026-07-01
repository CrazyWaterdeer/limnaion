from pathlib import Path

import pytest

from app import config, game_files
from app.types import StateUpdate


def _seed_templates(tmp_path: Path) -> Path:
    tdir = tmp_path / "templates"
    tdir.mkdir()
    for name in game_files.GAME_FILE_NAMES:
        (tdir / name).write_text(f"TEMPLATE {name}\n", encoding="utf-8")
    return tdir


@pytest.fixture
def patched(tmp_path, monkeypatch):
    games = tmp_path / "games"
    games.mkdir()
    tdir = _seed_templates(tmp_path)
    engine = tmp_path / "engine.md"
    engine.write_text("ENGINE RULES\n", encoding="utf-8")
    monkeypatch.setattr(config, "GAMES_DIR", games)
    monkeypatch.setattr(config, "TEMPLATES_DIR", tdir)
    monkeypatch.setattr(config, "ENGINE_MD", engine)
    return tmp_path


def test_write_text_atomic_replaces_content(tmp_path):
    p = tmp_path / "f.md"
    game_files.write_text_atomic(p, "first")
    game_files.write_text_atomic(p, "second")
    assert game_files.read_text(p) == "second"
    # the temp file was renamed away — only the final file remains
    assert list(tmp_path.iterdir()) == [p]


def test_new_game_copies_all_five_templates(patched):
    game_files.new_game_from_templates("demo")
    d = config.game_dir("demo")
    for name in game_files.GAME_FILE_NAMES:
        assert (d / name).read_text(encoding="utf-8") == f"TEMPLATE {name}\n"
    assert len(game_files.GAME_FILE_NAMES) == 5


def test_load_game_returns_populated(patched):
    game_files.new_game_from_templates("demo")
    g = game_files.load_game("demo")
    assert g.slug == "demo"
    assert g.engine == "ENGINE RULES\n"
    assert g.rules == "TEMPLATE rules.md\n"
    assert g.character == "TEMPLATE character.md\n"
    assert g.world == "TEMPLATE world.md\n"
    assert g.state == "TEMPLATE state.md\n"
    assert g.log == "TEMPLATE log.md\n"


def test_apply_state_update_appends_log_and_world(patched):
    game_files.new_game_from_templates("demo")
    d = config.game_dir("demo")
    upd = StateUpdate(
        new_state_md="NEW STATE",
        log_entry="## Turn 1\n- Action: look",
        world_additions="- a new fact",
        new_compact_state="compact",
    )
    game_files.apply_state_update("demo", upd)
    assert (d / "state.md").read_text(encoding="utf-8") == "NEW STATE"
    assert (d / "log.md").read_text(encoding="utf-8") == "TEMPLATE log.md\n\n## Turn 1\n- Action: look"
    assert (d / "world.md").read_text(encoding="utf-8") == "TEMPLATE world.md\n\n- a new fact"


def test_apply_state_update_skips_empty_world(patched):
    game_files.new_game_from_templates("demo")
    d = config.game_dir("demo")
    before = (d / "world.md").read_text(encoding="utf-8")
    upd = StateUpdate(
        new_state_md="S",
        log_entry="entry",
        world_additions="",
        new_compact_state="c",
    )
    game_files.apply_state_update("demo", upd)
    assert (d / "world.md").read_text(encoding="utf-8") == before


def test_delete_game_removes_directory(patched):
    game_files.new_game_from_templates("to-delete")
    assert config.game_dir("to-delete").exists()
    game_files.delete_game("to-delete")
    assert not config.game_dir("to-delete").exists()


def test_delete_game_noop_when_absent(patched):
    # Should not raise even if the slug does not exist.
    game_files.delete_game("nonexistent-slug")
