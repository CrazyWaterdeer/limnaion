#!/usr/bin/env bash
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
roll="$here/roll.sh"
fail=0
check() { # desc expected actual
  if [[ "$2" == "$3" ]]; then echo "ok: $1"; else echo "FAIL: $1 — expected '$2' got '$3'"; fail=1; fi
}
# Standard table
check "std 12 crit"    "CRITICAL SUCCESS" "$("$roll" band 12)"
check "std 11 success" "SUCCESS"          "$("$roll" band 11)"
check "std 10 success" "SUCCESS"          "$("$roll" band 10)"
check "std 9 partial"  "PARTIAL"          "$("$roll" band 9)"
check "std 8 partial"  "PARTIAL"          "$("$roll" band 8)"
check "std 7 partial"  "PARTIAL"          "$("$roll" band 7)"
check "std 6 failure"  "FAILURE"          "$("$roll" band 6)"
check "std 3 failure"  "FAILURE"          "$("$roll" band 3)"
check "std 2 critfail" "CRITICAL FAILURE" "$("$roll" band 2)"
# Wheelhouse table — note total 8 (PARTIAL->SUCCESS) and total 6 (FAILURE->PARTIAL) flip
check "wh 12 crit"     "CRITICAL SUCCESS" "$("$roll" band 12 wheelhouse)"
check "wh 11 success"  "SUCCESS"          "$("$roll" band 11 wheelhouse)"
check "wh 8 success"   "SUCCESS"          "$("$roll" band 8 wheelhouse)"
check "wh 7 partial"   "PARTIAL"          "$("$roll" band 7 wheelhouse)"
check "wh 6 partial"   "PARTIAL"          "$("$roll" band 6 wheelhouse)"
check "wh 5 failure"   "FAILURE"          "$("$roll" band 5 wheelhouse)"
check "wh 3 failure"   "FAILURE"          "$("$roll" band 3 wheelhouse)"
check "wh 2 critfail"  "CRITICAL FAILURE" "$("$roll" band 2 wheelhouse)"
exit $fail
