# tests/test_dice.py
"""Pure-Python dice tests — deterministic via injected _FixedRng, no subprocess."""
from __future__ import annotations

import pytest

from app.dice import roll_check, roll_oracle
from app.types import DiceResult


class _FixedRng:
    """RNG stub: returns a pre-loaded integer sequence from randint(), ignoring (a, b)."""

    def __init__(self, *values: int) -> None:
        self._q: list[int] = list(values)

    def randint(self, a: int, b: int) -> int:  # noqa: ARG002
        if not self._q:
            raise RuntimeError("_FixedRng exhausted — provide more values in the constructor")
        return self._q.pop(0)


# ---------------------------------------------------------------------------
# roll_check — Standard table  (thresholds: >=12 crit / >=10 success /
#                                >=7 partial / >=3 failure / <3 crit_fail)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "d1, d2, mod, expected_band",
    [
        # critical: total >= 12
        (6, 6, 0,  "critical"),          # total=12, lower edge of band
        (6, 6, 2,  "critical"),          # total=14, positive mod
        # success: 10 <= total < 12
        (5, 5, 0,  "success"),           # total=10, lower edge
        (6, 5, 0,  "success"),           # total=11, upper edge
        # partial: 7 <= total < 10
        (4, 3, 0,  "partial"),           # total=7,  lower edge
        (5, 4, 0,  "partial"),           # total=9,  upper edge
        # failure: 3 <= total < 7
        (2, 1, 0,  "failure"),           # total=3,  lower edge
        (3, 3, 0,  "failure"),           # total=6,  upper edge
        (3, 3, -2, "failure"),           # total=4,  negative mod
        # critical_failure: total < 3
        (1, 1, 0,  "critical_failure"),  # total=2
    ],
)
def test_roll_check_standard(d1: int, d2: int, mod: int, expected_band: str) -> None:
    result = roll_check(mod, "standard", rng=_FixedRng(d1, d2))
    assert result == DiceResult(total=d1 + d2 + mod, band=expected_band)


# ---------------------------------------------------------------------------
# roll_check — Wheelhouse table  (thresholds: >=12 crit / >=8 success /
#                                  >=6 partial / >=3 failure / <3 crit_fail)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "d1, d2, mod, expected_band",
    [
        # critical: total >= 12
        (6, 6, 0,  "critical"),          # total=12, lower edge
        (6, 6, 1,  "critical"),          # total=13, positive mod
        # success: 8 <= total < 12
        (4, 4, 0,  "success"),           # total=8,  lower edge
        (5, 6, 0,  "success"),           # total=11, upper edge
        # partial: 6 <= total < 8
        (3, 3, 0,  "partial"),           # total=6,  lower edge
        (4, 3, 0,  "partial"),           # total=7,  upper edge
        # failure: 3 <= total < 6
        (2, 1, 0,  "failure"),           # total=3,  lower edge
        (3, 2, 0,  "failure"),           # total=5,  upper edge
        (3, 3, -2, "failure"),           # total=4,  negative mod
        # critical_failure: total < 3
        (1, 1, 0,  "critical_failure"),  # total=2
    ],
)
def test_roll_check_wheelhouse(d1: int, d2: int, mod: int, expected_band: str) -> None:
    result = roll_check(mod, "wheelhouse", rng=_FixedRng(d1, d2))
    assert result == DiceResult(total=d1 + d2 + mod, band=expected_band)


# ---------------------------------------------------------------------------
# Divergence: totals where Standard and Wheelhouse assign different bands
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "d1, d2, standard_band, wheelhouse_band",
    [
        # total=9: std=[7-9]=partial, wh=[8-11]=success
        (5, 4, "partial", "success"),
        # total=8: std=[7-9]=partial, wh=[8-11]=success (lower edge of wh success)
        (5, 3, "partial", "success"),
        # total=6: std=[3-6]=failure, wh=[6-7]=partial (lower edge of wh partial)
        (4, 2, "failure", "partial"),
    ],
)
def test_table_divergence(
    d1: int, d2: int, standard_band: str, wheelhouse_band: str
) -> None:
    assert roll_check(0, "standard",   rng=_FixedRng(d1, d2)).band == standard_band
    assert roll_check(0, "wheelhouse", rng=_FixedRng(d1, d2)).band == wheelhouse_band


# ---------------------------------------------------------------------------
# roll_oracle
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "n, fixed_val, expected",
    [
        (1,  0, 0),   # single option, only possible index
        (3,  0, 0),   # first option in a list of 3
        (3,  2, 2),   # last option in a list of 3
        (5,  4, 4),   # last option in a list of 5
        (10, 7, 7),   # arbitrary mid-range
    ],
)
def test_roll_oracle_exact(n: int, fixed_val: int, expected: int) -> None:
    assert roll_oracle(n, rng=_FixedRng(fixed_val)) == expected


def test_roll_oracle_default_rng_in_range() -> None:
    """Default SystemRandom produces a valid 0-based index — no network needed."""
    for n in (2, 3, 5, 10):
        idx = roll_oracle(n)
        assert 0 <= idx < n, f"roll_oracle({n}) returned out-of-range index {idx}"


def test_roll_check_default_rng_smoke() -> None:
    """Default SystemRandom produces a valid DiceResult — no network needed."""
    result = roll_check(0, "standard")
    assert result.band in {"critical", "success", "partial", "failure", "critical_failure"}
    assert isinstance(result.total, int)
    assert 2 <= result.total <= 12  # 2d6 + mod 0
