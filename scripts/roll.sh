#!/usr/bin/env bash
# TRPG dice roller — real randomness, no LLM / python / uv needed.
#
# Usage:
#   roll.sh 2d6           sum of two six-sided dice
#   roll.sh 2d6+2         sum plus a modifier (also -K)
#   roll.sh d20           one twenty-sided die
#   roll.sh 3d8-1         any NdM(+/-K)
#   roll.sh pick N        uniform integer 1..N  (oracle: choose among N framed outcomes)
#   roll.sh band 9        band label for a known total on the Standard table
#   roll.sh band 9 wheelhouse   band label on the Wheelhouse table (a specialty applies)
#   roll.sh move +2       roll 2d6 + mod and print the result band (GM screen only)
#   roll.sh move +2 wheelhouse  same, banded on the Wheelhouse table
#
# Output of `move` shows numbers — that is for the GM, never paste it to the player when
# the game's visibility is hidden.
set -euo pipefail

die() { shuf -i "1-$1" -n 1; }

roll_xdy() {            # args: X Y -> echoes the summed roll
  local x="$1" y="$2" sum=0 i
  for ((i = 0; i < x; i++)); do sum=$((sum + $(die "$y"))); done
  echo "$sum"
}

band() {                # arg: total -> band label on the Standard table
  local t="$1"
  if   ((t >= 12)); then echo "CRITICAL SUCCESS"
  elif ((t >= 10)); then echo "SUCCESS"
  elif ((t >= 7));  then echo "PARTIAL"
  elif ((t >= 3));  then echo "FAILURE"
  else                   echo "CRITICAL FAILURE"
  fi
}

band_wheelhouse() {     # arg: total -> band label on the Wheelhouse table (specialty applies)
  local t="$1"
  if   ((t >= 12)); then echo "CRITICAL SUCCESS"
  elif ((t >= 8));  then echo "SUCCESS"
  elif ((t >= 6));  then echo "PARTIAL"
  elif ((t >= 3));  then echo "FAILURE"
  else                   echo "CRITICAL FAILURE"
  fi
}

band_for() {            # args: total [table] -> band label; "w"/"wheelhouse" => Wheelhouse
  local t="$1" tbl="${2:-}"
  case "$tbl" in
    w|wheelhouse|W|WHEELHOUSE) band_wheelhouse "$t" ;;
    *)                          band "$t" ;;
  esac
}

cmd="${1:-}"
case "$cmd" in
  pick)
    n="${2:?usage: roll.sh pick N}"
    shuf -i "1-$n" -n 1
    ;;
  band)
    t="${2:?usage: roll.sh band TOTAL [wheelhouse]}"
    band_for "$t" "${3:-}"
    ;;
  move)
    mod="${2:-+0}"
    tbl="${3:-}"
    base="$(roll_xdy 2 6)"
    total=$((base + (mod)))
    printf '2d6(%s) %s = %s -> %s\n' "$base" "$mod" "$total" "$(band_for "$total" "$tbl")"
    ;;
  "")
    echo "usage: roll.sh 2d6[+/-K] | dM | pick N | band TOTAL [wheelhouse] | move +/-K [wheelhouse]" >&2; exit 1
    ;;
  *)
    if [[ "$cmd" =~ ^([0-9]*)d([0-9]+)([+-][0-9]+)?$ ]]; then
      x="${BASH_REMATCH[1]:-1}"; y="${BASH_REMATCH[2]}"; mod="${BASH_REMATCH[3]:-0}"
      base="$(roll_xdy "$x" "$y")"
      total=$((base + (mod)))
      echo "$total"
    else
      echo "usage: roll.sh 2d6[+/-K] | dM | pick N | band TOTAL [wheelhouse] | move +/-K [wheelhouse]" >&2; exit 1
    fi
    ;;
esac
