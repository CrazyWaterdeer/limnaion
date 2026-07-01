"""Game file I/O: atomic writes, loading, and template scaffolding."""

import os
import tempfile
from pathlib import Path

from app import config
from app.types import GameFiles, StateUpdate

# The five per-game files copied from templates and loaded into GameFiles.
GAME_FILE_NAMES = ("rules.md", "character.md", "world.md", "state.md", "log.md")


def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text_atomic(path: Path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_game(slug: str) -> GameFiles:
    d = config.game_dir(slug)
    return GameFiles(
        slug=slug,
        # engine.md is loaded as the human-facing canonical ruleset and reference;
        # the runtime rule instructions live in REFEREE_SYSTEM/NARRATION_SYSTEM (distilled from it).
        engine=read_text(config.ENGINE_MD),
        rules=read_text(d / "rules.md"),
        character=read_text(d / "character.md"),
        world=read_text(d / "world.md"),
        state=read_text(d / "state.md"),
        log=read_text(d / "log.md"),
    )


def apply_state_update(slug: str, update: StateUpdate) -> None:
    d = config.game_dir(slug)
    write_text_atomic(d / "state.md", update.new_state_md)
    log = read_text(d / "log.md")
    write_text_atomic(d / "log.md", log + "\n" + update.log_entry)
    if update.world_additions.strip():
        world = read_text(d / "world.md")
        write_text_atomic(d / "world.md", world + "\n" + update.world_additions)


def new_game_from_templates(slug: str) -> None:
    d = config.game_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    for name in GAME_FILE_NAMES:
        content = read_text(config.TEMPLATES_DIR / name)
        write_text_atomic(d / name, content)


def delete_game(slug: str) -> None:
    """Permanently remove a game's folder under GAMES_DIR. No-op if absent."""
    import shutil
    d = config.game_dir(slug)
    if d.exists():
        shutil.rmtree(d)
