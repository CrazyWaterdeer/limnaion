from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Band = Literal["critical", "success", "partial", "failure", "critical_failure"]
Kind = Literal["impossible", "trivial", "uncertain"]
Mode = Literal["check", "oracle"]
Table = Literal["standard", "wheelhouse"]
Provider = Literal["claude-subscription", "openrouter"]


@dataclass(frozen=True)
class RoleConfig:
    provider: Provider
    model: str


@dataclass
class BandMeanings:
    critical: str
    success: str
    partial: str
    failure: str
    critical_failure: str


@dataclass
class UncertainSpec:
    mode: Mode
    attribute_or_track: str
    situational_mod: int
    total_mod: int
    table: Table
    specialty_applies: bool
    band_meanings: Optional[BandMeanings] = None
    oracle_options: Optional[list[str]] = None


@dataclass
class RefereeVerdict:
    kind: Kind
    reason: str
    uncertain: Optional[UncertainSpec] = None


@dataclass
class DiceResult:
    total: Optional[int] = None
    band: Optional[Band] = None
    picked_index: Optional[int] = None
    picked_option: Optional[str] = None


@dataclass
class StateUpdate:
    new_state_md: str
    log_entry: str
    world_additions: str
    new_compact_state: str


@dataclass
class NarrationRequest:
    narration_rules: str
    recent_turns_raw: list[str]
    compact_state: str
    player_input: str
    committed_outcome: Optional[str] = None
    visibility: str = "hidden"


@dataclass
class GameFiles:
    slug: str
    engine: str
    rules: str
    character: str
    world: str
    state: str
    log: str
