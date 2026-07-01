#!/usr/bin/env bash
# Gemini fallback narrator — renders ONE turn's narration prose via the Gemini CLI.
#
# Claude stays the referee: it interprets input, validates against canon, frames the
# bands, rolls real dice (roll.sh), commits the outcome, and records state. This script
# ONLY turns an already-decided outcome into Korean prose, and ONLY when the player
# explicitly asks for it ((gemini)/(제미니)/(폴백)).
#
# The brief on stdin is assembled by Claude and is a COMPLETE, self-contained prompt: it
# already carries the hard rules (Korean output, hide all numbers, no choice menus, do
# not author the character, full-paragraph depth) plus the current scene, the player's
# action, and the committed outcome. This script adds no judgment of its own.
#
# Usage:
#   printf '%s' "$BRIEF" | scripts/narrate_fallback.sh
#   printf '%s' "$BRIEF" | FALLBACK_TIMEOUT=90 scripts/narrate_fallback.sh
#
# Output:
#   success -> Gemini's Korean narration on stdout, exit 0.
#   failure (no key / gemini error / timeout / empty output) -> prints the marker
#           __FALLBACK_FAILED__ on stdout and exits non-zero, so the GM (Claude)
#           narrates the turn itself and the game never stalls.
#
# Env (mainly for tests):
#   FALLBACK_TIMEOUT  hard wall on the gemini call in seconds (default 60)
#   GEMINI_ENV_FILE   path to the key file to source (default ~/.gemini/.env)
set -uo pipefail

MARKER="__FALLBACK_FAILED__"
MODEL="gemini-3.5-flash"                         # fixed per design
TIMEOUT="${FALLBACK_TIMEOUT:-60}"
ENV_FILE="${GEMINI_ENV_FILE:-$HOME/.gemini/.env}"

fail() { printf '%s\n' "$MARKER"; exit 1; }

# Load the API key from its dedicated file. Sourcing here (not relying on the shell
# profile) makes it work even in a non-interactive shell, whose ~/.bashrc returns early.
if [ -f "$ENV_FILE" ]; then set -a; . "$ENV_FILE"; set +a; fi
[ -n "${GEMINI_API_KEY:-}" ] || fail

brief="$(cat)"
[ -n "$brief" ] || fail

# Headless call. CLI warnings (true-color, ripgrep) go to stderr and are discarded;
# only the narration reaches stdout.
out="$(timeout "$TIMEOUT" gemini -m "$MODEL" -p "$brief" -o text 2>/dev/null)"
[ $? -eq 0 ] || fail
[ -n "$out" ] || fail

printf '%s\n' "$out"
