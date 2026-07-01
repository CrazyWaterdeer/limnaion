# TRPG GM Framework — Project Guide

This folder is a reusable text-TRPG framework, not a single game. Full overview in `README.md`,
core rules in `engine.md`, design rationale in `docs/superpowers/specs/`.

## When the user wants to play

- **Start a new game** ("게임 시작하자", "새 게임", "trpg 하자") → use the **`trpg-new`** skill.
  The **player creates their own character** — elicit name, concept, background, personality, and
  strengths/weaknesses FROM them. Do **not** auto-author a character unless they explicitly ask
  for a suggestion. The player writes the *fiction*; you assign the *hidden stats* to match.
- **Continue an existing game** (a folder under `games/`) → use the **`trpg-play`** skill.
  If unsure which game, list `games/` and ask.

## House rules (always)

- **Randomness is real:** resolve every uncertain outcome with `scripts/roll.sh` (real RNG), never
  by preference. Frame the possible outcomes BEFORE rolling.
- **Hidden by default:** never show the player stat numbers or dice values unless that game's
  `rules.md` sets `visibility: shown`. Convey competence and harm as feeling, not numbers.
- **Language:** files under `games/`, `templates/`, etc. are **English** (token-efficient); narrate
  to the player in **Korean**.
- **Offload the busywork:** file bookkeeping → `trpg-scribe` agent; log compression →
  `trpg-archivist` agent (both on a cheap model). The main model handles judgment and narration.
