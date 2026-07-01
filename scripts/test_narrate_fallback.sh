#!/usr/bin/env bash
# Hermetic tests for narrate_fallback.sh — never calls the real Gemini API; a stub
# `gemini` on PATH simulates each outcome. Verifies the key guard, the error marker,
# verbatim passthrough on success, and the timeout safety net.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script="$here/narrate_fallback.sh"
fail=0
check() { # desc expected actual
  if [[ "$2" == "$3" ]]; then echo "ok: $1"; else echo "FAIL: $1 — expected '$2' got '$3'"; fail=1; fi
}

MARKER="__FALLBACK_FAILED__"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

keyfile="$tmp/env"; printf 'GEMINI_API_KEY=test-key\n' > "$keyfile"

make_stub() { # mode -> echoes a bin dir holding a fake `gemini`
  local mode="$1"
  local bindir="$tmp/bin_$mode"
  mkdir -p "$bindir"
  case "$mode" in
    ok)    printf '#!/usr/bin/env bash\necho "스텁 서술 결과"\n'        > "$bindir/gemini" ;;
    empty) printf '#!/usr/bin/env bash\nexit 0\n'                       > "$bindir/gemini" ;;
    err)   printf '#!/usr/bin/env bash\necho boom >&2\nexit 3\n'        > "$bindir/gemini" ;;
    slow)  printf '#!/usr/bin/env bash\nsleep 5\necho "too late"\n'     > "$bindir/gemini" ;;
  esac
  chmod +x "$bindir/gemini"
  echo "$bindir"
}

run() { # envfile bindir timeout stdin -> sets OUT, RC
  OUT="$(printf '%s' "$4" | GEMINI_ENV_FILE="$1" FALLBACK_TIMEOUT="$3" PATH="$2:$PATH" GEMINI_API_KEY= bash "$script")"
  RC=$?
}
nonzero() { [ "$1" -ne 0 ] && echo 1 || echo 0; }

# 1. no key file present -> marker, nonzero
run "$tmp/nope" "$(make_stub ok)" 60 "brief here"
check "no key -> marker"   "$MARKER" "$OUT"
check "no key -> nonzero"  "1"       "$(nonzero "$RC")"

# 2. empty brief -> marker
run "$keyfile" "$(make_stub ok)" 60 ""
check "empty brief -> marker" "$MARKER" "$OUT"

# 3. gemini exits non-zero -> marker
run "$keyfile" "$(make_stub err)" 60 "brief"
check "gemini error -> marker" "$MARKER" "$OUT"

# 4. gemini exits 0 but prints nothing -> marker
run "$keyfile" "$(make_stub empty)" 60 "brief"
check "gemini empty -> marker" "$MARKER" "$OUT"

# 5. success -> verbatim passthrough, rc 0
run "$keyfile" "$(make_stub ok)" 60 "brief"
check "success passthrough" "스텁 서술 결과" "$OUT"
check "success rc 0"        "0"            "$RC"

# 6. call hangs past the timeout -> marker (safety net)
run "$keyfile" "$(make_stub slow)" 1 "brief"
check "timeout -> marker" "$MARKER" "$OUT"

exit $fail
