from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from app import game_files, orchestrator


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="app.main", description="TRPG GM framework CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="scaffold a new game from templates")
    p_new.add_argument("slug", help="game folder name under games/")

    p_play = sub.add_parser("play", help="play/resume an existing game")
    p_play.add_argument("slug", help="game folder name under games/")

    p_tui = sub.add_parser("tui", help="open the Limnaion TUI (no slug -> splash hub)")
    p_tui.add_argument("slug", nargs="?", default=None,
                       help="game folder under games/ (optional; omit for the splash hub)")

    args = parser.parse_args(argv)
    if args.command == "new":
        game_files.new_game_from_templates(args.slug)
    elif args.command == "play":
        orchestrator.run_repl(args.slug)
    elif args.command == "tui":
        from app.tui.app import run_play  # lazy: only the TUI path imports Textual
        run_play(args.slug)
    return 0


def limnaion() -> None:
    """Console-script entry point: `limnaion` opens the splash hub; `limnaion <slug>`
    jumps straight into that saved game."""
    import sys
    from app.tui.app import run_play
    run_play(sys.argv[1] if len(sys.argv) > 1 else None)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
