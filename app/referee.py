import json
import re
from typing import Optional

from . import config, context, dice, providers
from .types import (
    BandMeanings,
    DiceResult,
    RefereeVerdict,
    RoleConfig,
    UncertainSpec,
)

REFEREE_SYSTEM = """\
You are the REFEREE of a text TRPG. You do NOT narrate. You classify the player's intended
action against the rules and the recorded fiction, then emit ONE strict JSON object and
nothing else.

Classify `kind` as exactly one of:
- "impossible": the action cannot succeed given established facts (it simply fails).
- "trivial": a routine, unpressured action the character is good at, or one with no
  interesting failure (it simply succeeds). Do NOT roll these.
- "uncertain": the outcome is in genuine doubt AND failure is interesting. Only these roll.

For "uncertain", fill `uncertain` with:
- "mode": "check" when competence matters (a character attempts something); "oracle" when
  the answer is pure chance the character cannot influence.
- "attribute_or_track": the fitting attribute (Might/Agility/Wits/Presence) or a game's
  specialized track. For oracle use the relevant track or "fate".
- "situational_mod": one integer in -2..+2 from the fiction (-2 very unfavorable, -1
  unfavorable, 0 even, +1 favorable, +2 very favorable).
- "specialty_applies": true if one of the character's tagged specialties clearly applies.
- "table": "wheelhouse" when a specialty applies (competence-forward), else "standard".
- "total_mod": the attribute/track modifier PLUS situational_mod — the number handed to dice.
- mode "check": COMMIT "band_meanings" NOW, before any roll — a concrete sentence for each
  band, consistent with character.md, world, and state. Use EXACTLY these five JSON keys:
  "critical" (the critical SUCCESS), "success", "partial", "failure", "critical_failure".
  Set "oracle_options" null.
- mode "oracle": list 2+ plausible "oracle_options" consistent with the facts. Set
  "band_meanings" null.

Output ONLY this JSON (no prose, no code fence):
{"kind": "...", "reason": "...", "uncertain": {...} or null}
For "trivial"/"impossible", set "uncertain" to null.
"""

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _strip_fences(raw: str) -> str:
    m = _FENCE_RE.search(raw)
    return m.group(1) if m else raw.strip()


def parse_verdict(raw: str) -> RefereeVerdict:
    data = json.loads(_strip_fences(raw))
    uncertain = None
    u = data.get("uncertain")
    if u is not None:
        bm = None
        b = u.get("band_meanings")
        if b is not None:
            def _band(key, *aliases):
                for k in (key, *aliases):
                    if k in b:
                        return b[k]
                raise KeyError(f"band_meanings missing {key!r}")

            bm = BandMeanings(
                # The crit-success band is keyed "critical" in our schema, but models
                # routinely emit "critical_success" — accept either.
                critical=_band("critical", "critical_success", "crit_success"),
                success=_band("success"),
                partial=_band("partial"),
                failure=_band("failure"),
                critical_failure=_band("critical_failure", "crit_failure"),
            )
        uncertain = UncertainSpec(
            mode=u["mode"],
            attribute_or_track=u["attribute_or_track"],
            situational_mod=u["situational_mod"],
            total_mod=u["total_mod"],
            table=u["table"],
            specialty_applies=u["specialty_applies"],
            band_meanings=bm,
            oracle_options=u.get("oracle_options"),
        )
    return RefereeVerdict(kind=data["kind"], reason=data["reason"], uncertain=uncertain)


def adjudicate(
    referee_rules: str,
    character_md: str,
    compact_state: str,
    player_input: str,
    *,
    role: RoleConfig = config.REFEREE,
    complete=providers.complete,
) -> RefereeVerdict:
    prompt = context.referee_context(referee_rules, character_md, compact_state, player_input)
    raw = complete(role, REFEREE_SYSTEM, prompt, json_out=True)
    return parse_verdict(raw)


def resolve_dice(
    verdict: RefereeVerdict,
    *,
    roll_check=dice.roll_check,
    roll_oracle=dice.roll_oracle,
) -> tuple[Optional[DiceResult], Optional[str]]:
    if verdict.kind != "uncertain" or verdict.uncertain is None:
        return None, None
    spec = verdict.uncertain
    if spec.mode == "check":
        result = roll_check(spec.total_mod, spec.table)
        if spec.band_meanings is None:
            raise ValueError("check verdict is missing band_meanings — model violated the schema")
        committed = getattr(spec.band_meanings, result.band)
        return result, committed
    options = spec.oracle_options
    if not options:
        raise ValueError("oracle verdict has no oracle_options — model violated the schema")
    idx = roll_oracle(len(options))
    result = DiceResult(picked_index=idx, picked_option=options[idx])
    return result, options[idx]
