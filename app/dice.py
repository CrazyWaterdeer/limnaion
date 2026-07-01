# app/dice.py
"""Pure-Python dice resolution — no subprocess, no bash dependency.

scripts/roll.sh is kept as a standalone Unix CLI for human use;
the application no longer shells out to it.
"""
from __future__ import annotations

import random

from app.types import Band, DiceResult, Table

# Module-level default RNG: OS entropy via SystemRandom, never seeded.
_rng = random.SystemRandom()


def _band_standard(total: int) -> Band:
    """Map a 2d6+mod total to a band on the Standard table."""
    if total >= 12:
        return "critical"
    if total >= 10:
        return "success"
    if total >= 7:
        return "partial"
    if total >= 3:
        return "failure"
    return "critical_failure"


def _band_wheelhouse(total: int) -> Band:
    """Map a 2d6+mod total to a band on the Wheelhouse table (specialty applies)."""
    if total >= 12:
        return "critical"
    if total >= 8:
        return "success"
    if total >= 6:
        return "partial"
    if total >= 3:
        return "failure"
    return "critical_failure"


def roll_check(mod: int, table: Table, *, rng=_rng) -> DiceResult:
    """Roll 2d6, add mod, and classify the total on the chosen band table.

    Args:
        mod:   Integer modifier (positive or negative) added to the 2d6 sum.
        table: ``"standard"`` or ``"wheelhouse"`` — selects threshold set.
        rng:   Object exposing ``randint(a, b)`` (inclusive). Defaults to the
               module-level ``SystemRandom`` instance. Inject a deterministic
               stub in tests.

    Returns:
        :class:`~app.types.DiceResult` with ``total`` and ``band`` set;
        ``picked_index`` and ``picked_option`` are ``None``.
    """
    d1: int = rng.randint(1, 6)
    d2: int = rng.randint(1, 6)
    total: int = d1 + d2 + mod
    band: Band = _band_wheelhouse(total) if table == "wheelhouse" else _band_standard(total)
    return DiceResult(total=total, band=band)


def roll_oracle(n: int, *, rng=_rng) -> int:
    """Return a uniform 0-based index in ``[0, n)``.

    Args:
        n:   Number of oracle options to choose among.
        rng: Object exposing ``randint(a, b)`` (inclusive). Defaults to the
             module-level ``SystemRandom`` instance.

    Returns:
        A 0-based integer index. The caller (``app.referee``) constructs
        the full :class:`~app.types.DiceResult` from it.
    """
    return rng.randint(0, n - 1)
