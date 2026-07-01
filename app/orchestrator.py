from __future__ import annotations

import sys
from dataclasses import dataclass

from app import config, context, game_files, narrator, referee, scribe
from app.providers import ModelError
from app.context import RecentTurns
from app.types import GameFiles, RefereeVerdict

# FIX 2: module-level sentinel so run_repl can detect narration failure without
# reprinting normal streamed prose.
NARRATION_FAILURE_SENTINEL = "(서술 생성에 실패했습니다 — 다시 시도해 주세요.)"


@dataclass
class Session:
    slug: str
    game: GameFiles
    recent: RecentTurns
    compact_state: str


def load_session(slug: str) -> Session:
    game = game_files.load_game(slug)
    recent = RecentTurns(config.RECENT_TURNS_K)
    return Session(
        slug=slug,
        game=game,
        recent=recent,
        compact_state=game.state,
    )


def play_turn(
    session: Session,
    player_input: str,
    *,
    adjudicate=referee.adjudicate,
    resolve_dice=referee.resolve_dice,
    narrate=narrator.narrate,
    record=scribe.record,
    compress_log=scribe.compress_log,  # FIX 5: injectable for testing
) -> str:
    try:
        verdict = adjudicate(
            session.game.rules,
            session.game.character,
            session.compact_state,
            player_input,
        )
    except ModelError as exc:
        # Referee failed even after the backend's retry: downgrade to a no-roll
        # turn (trivial verdict -> no dice, no committed outcome) and keep playing.
        print(f"[warn] adjudicate failed; downgrading to no-roll turn: {exc}", file=sys.stderr)
        verdict = RefereeVerdict(kind="trivial", reason="referee unavailable (degraded turn)")

    if verdict.kind == "uncertain":
        dice, committed_outcome = resolve_dice(verdict)
    elif verdict.kind == "impossible":
        dice = None
        committed_outcome = (
            f"The action is impossible: {verdict.reason}. "
            "Narrate, in fiction, why it cannot happen — it does not succeed."
        )
    else:  # trivial (also the downgraded-on-failure path: no dice, no committed outcome)
        dice, committed_outcome = None, None

    visibility = "shown" if "visibility: shown" in session.game.rules else "hidden"
    req = context.build_narration_request(
        session.game.rules,
        session.recent,
        session.compact_state,
        player_input,
        committed_outcome,
        visibility,
    )

    try:
        text = "".join(narrate(req))
    except ModelError as exc:
        # Narrator failed even after the backend's retry: surface an honest sentinel
        # and SKIP record — never fabricate prose, never record an empty turn.
        print(f"[warn] narrate failed; returning sentinel: {exc}", file=sys.stderr)
        return NARRATION_FAILURE_SENTINEL  # FIX 2: return constant, not literal

    try:
        update = record(session.game, player_input, text, dice)
    except ModelError as exc:
        # Scribe failed even after the backend's retry: keep the narration the player
        # already saw. Append to recent and return it, but leave the game files and
        # compact_state untouched so the turn can be re-recorded later.
        print(f"[warn] record failed; keeping narration, skipping state update: {exc}", file=sys.stderr)
        session.recent.add(player_input, text)
        return text

    game_files.apply_state_update(session.slug, update)
    session.recent.add(player_input, text)
    session.compact_state = update.new_compact_state
    # FIX 1: reload game files so the next turn's scribe sees the just-written state.
    session.game = game_files.load_game(session.slug)
    # FIX 5: compress log if it has grown past the threshold.
    if len(session.game.log.splitlines()) > config.LOG_COMPRESS_THRESHOLD:
        try:
            new_log = compress_log(session.game)
            game_files.write_text_atomic(config.game_dir(session.slug) / "log.md", new_log)
            session.game = game_files.load_game(session.slug)
        except ModelError as exc:
            print(f"[warn] log compression failed: {exc}", file=sys.stderr)
    return text


def _streaming_narrate(req):
    for chunk in narrator.narrate(req):
        print(chunk, end="", flush=True)
        yield chunk


def run_repl(slug: str) -> None:
    session = load_session(slug)
    while True:
        try:
            player_input = input("\n> ").strip()
        except EOFError:
            break
        if not player_input:
            continue
        # FIX 3: per-turn exception guard — a bad verdict/scribe/roll aborts only the turn.
        try:
            result = play_turn(session, player_input, narrate=_streaming_narrate)
        except Exception as exc:
            print(f"[turn error] {exc}", file=sys.stderr)
            continue
        # FIX 2: sentinel was never streamed, so print it explicitly so the player sees it.
        if result == NARRATION_FAILURE_SENTINEL:
            print(result)
        print()
