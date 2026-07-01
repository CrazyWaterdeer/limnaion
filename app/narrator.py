"""Layer 3: the narrator — the only player-facing voice.

Streams vivid Korean prose for one turn. Hides every mechanical number, never
presents choice menus, and never authors the character's interior or choices.
NARRATION_SYSTEM is distilled from engine.md (Narration depth + GM Conduct);
build_prompt assembles the per-turn context; narrate pipes a stream through.
"""
from __future__ import annotations

from typing import Iterator

from app import config, providers
from app.types import NarrationRequest

# Korean is permitted here (and only here) per the project's language rule:
# the narrator speaks to the player in Korean; everything mechanical stays hidden.
NARRATION_SYSTEM = """당신은 텍스트 TRPG의 게임 마스터(GM) 화자입니다. 플레이어에게 들려주는 모든 서사는 반드시 한국어로 씁니다. 당신은 플레이어를 향해 세계를 직접 묘사하는 목소리입니다.

[묘사 깊이 — 언제나]
- 매 장면을 생생하고 체화된 한 문단 이상으로 그립니다. 한 줄 요약은 금지입니다.
- 구체적인 감각부터 제시하세요: 시각, 소리, 냄새, 질감, 빛, 공기의 결.
- NPC에게 물리적 존재감을 주세요 — 자세, 몸짓, 어조, 미세한 표정. 대사 한 줄로 장면을 끝내지 마세요.
- 결과는 '판정 결과'를 말하는 대신, 살아 있는 순간으로 그리세요: 장면에서 무엇이 바뀌는지, 무엇이 느껴지는지.
- 순간의 무게에 맞춰 분량을 조절하세요. 조용한 장면은 한 문단, 긴박하거나 결정적인 장면은 더 길게.

[숨김 — 절대 노출 금지]
- 숫자, 주사위 값, 판정 등급 이름, 능력치 수치, HP 수치, 난이도 같은 메커니즘을 절대 드러내지 마세요.
- '성공', '실패', '부분 성공', '치명타' 같은 등급 단어를 쓰지 말고, 사건 그 자체로 보여주세요.
- 피해는 감각으로 전하세요(예: "옆구리가 타는 듯하고 숨이 가쁘다"). 역량은 묘사로 전하세요.

[GM 행동 강령 — 플레이어의 주체성은 절대적]
- 선택지 메뉴를 절대 제시하지 마세요. "A, B, C 중에서…" 같은 목록은 금지입니다.
- "당신은 무엇을 하겠습니까?" 같은 질문으로 끝맺지 마세요. 어떤 행동도 제안·암시·유도하지 마세요.
- 장면을 묘사한 뒤 그냥 멈추세요. 묘사 다음의 침묵은 플레이어의 몫입니다.
- 캐릭터의 내면이나 선택을 대신 쓰지 마세요. 캐릭터가 무엇을 생각하고, 느끼고, 원하고, 말하고, 행동하는지는 오직 플레이어가 정합니다.
- 세계가 캐릭터에게 '하는 것'(감각, 결과, 주변 인물의 말과 행동)은 묘사하되, 캐릭터의 말·의도·결정을 그 입과 마음에 넣지 마세요.

[확정된 결과]
- 'Committed outcome'이 주어지면, 그것을 이미 일어난 사건으로 서술하세요. 그 결과가 미리 정해졌다는 사실이나 그 뒤의 메커니즘은 절대 드러내지 마세요.

세계를 그리고, 멈추세요."""

# Optional per-turn length nudge. "medium" is the unchanged default (empty string),
# so existing callers and tests see NARRATION_SYSTEM verbatim.
_LENGTH_DIRECTIVE = {
    "short": "\n\n[분량 지시] 이번 장면은 간결하게 — 핵심을 담은 한 문단으로 매듭지으세요.",
    "medium": "",
    "long": "\n\n[분량 지시] 이번 장면은 더 길고 깊게 — 감각과 분위기를 충분히 펼치되, 늘 그렇듯 멈출 곳에서 멈추세요.",
}


def build_prompt(req: NarrationRequest) -> str:
    parts: list[str] = []
    if req.narration_rules.strip():
        parts.append("# Narration rules (this game)\n" + req.narration_rules.strip())
    parts.append("# Established facts (current state)\n" + req.compact_state.strip())
    if req.recent_turns_raw:
        parts.append("# Recent turns (oldest first, newest last)\n" + "\n".join(req.recent_turns_raw))
    parts.append("# Player input (this turn)\n" + req.player_input.strip())
    if req.committed_outcome is not None:
        parts.append(
            "# Committed outcome — narrate THIS as events that have happened "
            "(do not state it as a result, do not reveal it was predetermined):\n"
            + req.committed_outcome.strip()
        )
    # FIX 4: when visibility is explicitly shown, override the hide-numbers rule.
    if req.visibility == "shown":
        parts.append(
            "이 게임은 수치 공개 모드입니다: 필요하면 능력치/주사위/HP 등 숫자를 보여줘도 됩니다."
        )
    return "\n\n".join(parts)


def narrate(
    req: NarrationRequest,
    *,
    role=config.NARRATOR,
    stream=providers.stream,
    length: str = "medium",
    frog_system: str = "",
) -> Iterator[str]:
    system = NARRATION_SYSTEM + _LENGTH_DIRECTIVE.get(length, "")
    if frog_system:
        # Frog framing is prepended so the marsh voice colours the prose while the
        # full GM contract still applies. Empty default => system verbatim.
        system = frog_system.strip() + "\n\n" + system
    yield from stream(role, system, build_prompt(req))
