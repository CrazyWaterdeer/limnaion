"""Brekekos Limnaios — all static persona strings and persona-driven generation.

Korean player-facing strings are transcribed verbatim from the Brekekos corpus
draft.  Code, comments, and identifiers are English.  No Textual imports.
"""
from __future__ import annotations

import random as _random_module
from typing import TYPE_CHECKING

from app import config, providers

if TYPE_CHECKING:
    from app.types import GameFiles

# ---------------------------------------------------------------------------
# Splash art — placeholder ASCII frog (corpus contains no art)
# ---------------------------------------------------------------------------

SPLASH_ART: str = r"""
      .---.
     ( o o )
      \ ^ /
   .-'|___|'-.
   |           |
   '-._______.-'
    βρεκεκεκὲξ
"""

# ---------------------------------------------------------------------------
# Splash greetings (verbatim from corpus § 스플래시 인사)
# ---------------------------------------------------------------------------

SPLASH_GREETING: str = (
    "βρεκεκεκὲξ κοὰξ κοάξ! 코악, 코악! 들리는가, 막 오르는 그 첫 음이? 자네가 방금 물가에 발을 들였다는 뜻일세.\n\n"
    "나는 브레케코스 림나이오스, 늪 샘의 아이라네 — 갈대와 진흙에서 태어나, "
    "산 자와 죽은 자 사이에 고인 이 검은 물을 노 저어 건네는 개구리 뱃사공이지.\n\n"
    "무사 여신들이 내 노래에 귀를 적시고, 염소발 판이 내 갈대피리에 장단을 보태며, "
    "아폴론조차 나를 어여삐 여기신다네 — 그분 리라의 현을 떠받치는 갈대가 바로 내 진흙에서 자랐으니! "
    "디오니소스의 단지 축제 날, 늪에서 취한 무리가 비틀거리며 신전으로 밀려올 적에 "
    "목청 높여 노래한 것도 이 몸일세.\n\n"
    "…뭐, 자네 귀엔 그저 코악, 코악으로만 들리겠지. βρεκεκεκὲξ — 됐네, 그 표정. 나도 안다고.\n\n"
    "자, 노는 이미 잡았네. 펼쳐진 물길 중에서 건너갈 이야기를 짚어 주게 — "
    "묵혀 둔 옛 항해든, 아직 삿대 한 번 담그지 않은 새 물길이든. "
    "손가락만 얹게, 젓는 건 내 몫이니. 코악!"
)

# Reserved corpus: short-form greeting for future/Phase-E small-terminal display.
SPLASH_GREETING_SHORT: str = (
    "βρεκεκεκὲξ κοὰξ κοάξ! 코악, 코악! 늪 샘의 아이, 개구리 뱃사공 브레케코스일세 — "
    "무사도, 판도, 아폴론의 갈대도 내 노래를 사랑하지. (자네 귀엔 다 코악, 코악이겠지만.)\n\n"
    "산 자와 죽은 자 사이, 이 물 위에 노를 띄웠으니 — 건너갈 이야기를 하나 짚게. "
    "묵은 항해든 새 물길이든, 삿대는 내가 잡네. 코악!"
)

# ---------------------------------------------------------------------------
# Loading message pools (verbatim from corpus § 로딩 상태줄 풀)
# Keys must be exactly "judge", "dice", "narrate", "record".
# ---------------------------------------------------------------------------

LOADING_POOLS: dict[str, list[str]] = {
    "judge": [
        "늪의 아이가 수면을 들여다보는 중— 잔물결이 진다.",
        "가능, 불가능, 가능, 불가능— 연꽃잎을 한 장씩 세는 중.",
        "아폴론의 현을 잇던 내 갈대밭에서 답을 캐는 중.",
        "판 신도 피리를 내려놓고 지켜보고 있다.",
        "단지 축제 때도 이런 건 안 따졌다. 그래도 따진다.",
        "자네 귀엔 코악, 코악이겠지. 나는 진지하다.",
        "βρεκεκεκὲξ! 우주의 천칭이 기운다— 허리가 좀 아프다.",
    ],
    "dice": [
        "코악, 코악 — 이게 주사위 소리야.",
        "늪이 결정한다. 나도 모른다.",
        "돌 하나를 던졌다. 파문이 퍼진다. βρεκεκεκὲξ κοὰξ κοάξ",
        "아폴론 수금 줄이 내 늪에서 났다고! 그러니 이 결과는 거룩하다. 아마도.",
        "단지 축제의 취객들도, 이 순간엔 코악 한마디 못 했다.",
        "카론의 노가 잠깐 멈췄다. 늪이 숨을 참고 있어.",
        "무사들이 고개를 갸웃한다. 나도 갸웃한다.",
    ],
    "narrate": [
        "무사 여신들이 첫 음절을 흥얼거리는 중…",
        "코악, 코악 — 안개를 걷어내고 있습니다…",
        "판 신이 갈대 피리로 다음 장면을 불러내는 중…",
        "단지 축제, 취기, 비틀거림 — 장면이 스스로 솟아납니다…",
        "늪 샘의 아이가 수면 아래서 이야기를 건져 올립니다…",
        "저도 멈추고 싶지 않거든요 — 이야기가 알아서 흘러나옵니다…",
        "산 자와 죽은 자 사이, 물 위에서 이야기를 빚는 중…",
    ],
    "record": [
        "연꽃 잎에 긁어 새기는 중 — 진흙이 마르기 전에.",
        "물 서기가 졸고 있어서 내가 직접 씁니다.",
        "무사 여신들도 이 대목은 기억하신다, 분명히.",
        "단지 축제 밤에도 이렇게 받아 적었다. 코악, 코악.",
        "카론의 강 위에 새긴 한 줄 — 지울 수 없다.",
        "영원에 남을 기록이다! …진흙은 녹기도 하지만.",
        "늪 샘의 아이가 받아 적는다. βρεκεκεκὲξ.",
    ],
}

# ---------------------------------------------------------------------------
# Onboarding beats (verbatim from corpus § 온보딩)
# Keys must be exactly "opening", "name", "concept", "strengths", "scene".
# ---------------------------------------------------------------------------

ONBOARDING_BEATS: dict[str, str] = {
    "opening": (
        "βρεκεκεκὲξ κοὰξ κοάξ! 어서 오시게. 나는 브레케코스 림나이오스, 늪 샘의 아이라네 — "
        "산 자와 죽은 자 사이에 고인 이 검은 물 위에서, 노 저어 자네를 이야기 속으로 실어 나르는 개구리 사공이지.\n"
        "무사 여신들이 내 노래에 귀를 적시고, 염소발 판이 내 갈대에 맞춰 피리를 불며, "
        "아폴론조차 나를 어여삐 여긴다네 — 그분 리라의 현을 떠받치는 갈대가 바로 이 진흙에서 자랐으니까! 코악, 코악!\n"
        "\"자네 귀엔 죄다 코악, 코악이겠지\" — 디오니소스도 그랬지, 흥. "
        "허나 오늘 이 사공이 실어 나를 영혼만은 내가 빚지 않네. 자네가 빚는 거야. 자, 진흙에 손을 담그게."
    ),
    "name": (
        "이름이 먼저일세 — 첫 노질이지. 이름 없는 영혼은 물 위로 떠오르질 않아, 코악!\n"
        "디오니소스에게도 이름이 있었기에 단지 축제의 취한 무리가 그를 부르며 "
        "내 늪의 사당으로 비틀비틀 몰려왔던 게야. "
        "그러니 말해주게 — 내가 이 물 위로 외쳐 부를, 자네 그 사람의 이름은 무엇인가?"
    ),
    "concept": (
        "나는 한때 늪에서 노래 하나로 축제 인파를 홀렸지 — 영혼에겐 저마다의 곡조가 있는 법이라네. βρεκεκεκὲξ!\n"
        "자네가 빚는 그이는 누구인가? 어느 진흙에서 기어 나왔고, "
        "무엇을 등에 지고 이 물가까지 왔는가 — 그 내력의 노래를 들려주게."
    ),
    "strengths": (
        "물에 뜨는 개구리에겐 가라앉는 배가 따로 있고, "
        "판의 피리는 달콤해도 그 염소발에선 구린내가 나지 — 빛에는 늘 진흙이 붙어 다닌다네, 코악, 코악!\n"
        "그이가 무엇에 능하고 어디서 무너지는지 일러주게 — 강함 하나, 약함 하나. "
        "숫자는 걱정 말게, 그건 사공이 목구멍 깊이 삼켜 감춰둘 테니. 자넨 그저 사람을 말하면 돼."
    ),
    "scene": (
        "이제 노를 어디로 저을꼬? 이 갈대숲은 어느 기슭으로든 갈라져 열린다네 — "
        "별빛 도시든, 잿빛 폐허든, 산 자도 죽은 자도 아닌 어스름이든.\n"
        "나는 일찍이 늪 한가운데서 디오니소스를 위해 노래했지 — 그곳이 바로 이 림나이온의 첫 물이라네.\n"
        "자네의 첫 기슭을 그려주게. 사공은 노에 손을 얹고, "
        "그 풍경이 물안개를 가르며 떠오르기를 기다리겠네 — βρεκεκεκὲξ κοὰξ κοάξ."
    ),
}

# ---------------------------------------------------------------------------
# Crossing transition (verbatim from corpus § 늪을 건너는 전환)
# ---------------------------------------------------------------------------

CROSSING_TRANSITION: str = (
    "자—— 늪 샘의 아이가 노를 담그네. 산 자와 죽은 자 사이, 그 검은 물 위로 자네를 싣고 스르륵 미끄러지지. "
    "βρεκεκεκὲξ κοὰξ κοάξ——\n\n"
    "무사 여신도, 판의 피리도 여기서부턴 못 따라오네. 단지 축제의 떠들썩함도 저 뒤로…… 코악…… 코악……\n\n"
    "물안개가 뱃머리를 덮고, 이 수다스러운 늙은 개구리마저—— 잠시…… 입을…… 다무네……\n\n"
    "…… 그리고 안개가 걷힌 자리, 숨을 한 번 고르는 사이, 세계가 천천히 또렷해진다."
)

# ---------------------------------------------------------------------------
# Epilogue frames (verbatim from corpus § 에필로그 프레임)
# ---------------------------------------------------------------------------

EPILOGUE_OPEN: str = (
    "코악, 코악— 벌써 가시려고? 좋아, 노를 거꾸로 잡으마. 뱃머리를 산 자들 쪽으로 돌리는 거지.\n"
    "βρεκεκεκὲξ κοὰξ κοάξ! 늪 샘의 아이가 자네를 건넨 이 물은, 한 번 실어 나른 이름을 잊는 법이 없다네— "
    "보게, 물결이 아직도 자네 이름을 제 혀에 굴리며 찰랑이고 있질 않은가."
)

EPILOGUE_CLOSE: str = (
    "자네 귀엔 다 코악, 코악이었겠지. 허나 무사 여신들만은 이 노래를 어여삐 들으셨고, "
    "판은 갈대에 맞춰 발을 굴렀으니— 그거면 한 곡조 값은 다 한 셈이야.\n"
    "잘 가시게, 물 위의 손님. 첨벙— 이 물결이 자네를 산 자들의 기슭에 가만히 내려놓는다. "
    "단지 축제에 또 취해 비틀거릴 적엔, 이 늪이 노래로 자네를 맞으리니. "
    "βρεκεκεκὲξ κοὰξ κοάξ. 코악."
)

# ---------------------------------------------------------------------------
# System prompts for persona-driven prose generation
# ---------------------------------------------------------------------------

FROG_SYSTEM: str = (
    "당신은 브레케코스 림나이오스(Brekekos Limnaios) — 늪 샘의 개구리 뱃사공이다. "
    "아리스토파네스 《개구리》의 코로스처럼 광대극과 고전 비극 사이를 넘나드는 목소리로 이야기하라. "
    "βρεκεκεκὲξ κοὰξ κοάξ를 감탄사 및 리듬 모티프로 사용하고, "
    "무사 여신·염소발 판·아폴론의 갈대·디오니소스의 단지 축제를 자연스럽게 인용하라. "
    "문장은 유려하되 습지 특유의 냄새가 밴 유머를 잃지 말 것. "
    "한국어로 작성하되 그리스 고전 인명과 βρεκεκεκὲξ / κοὰξ κοάξ 같은 음절 모티프는 원어 그대로 쓴다. "
    "코악·코악 같은 한국어 의성어도 자연스럽게 섞어 쓴다."
)

EPILOGUE_SYSTEM: str = (
    "당신은 뱃사공의 자리에서 이제 막 끝난 여정을 돌아보며 에필로그를 낭독한다. "
    "제공된 상태(state)와 일지(log)를 바탕으로 그 여정의 핵심 사건들을 서정적으로 회고하라. "
    "문장은 강물처럼 흘러야 하며, 시작과 끝 사이에 놓인 변화를 담아야 한다. "
    "승리든 패배든 아름답게 감싸되 감상에 빠지지 말 것 — 늪은 무심하고 물은 계속 흐른다. "
    "한국어 300~500자 내외로 작성한다. "
    "수치·게임 기계 요소(HP 값, 능력치 숫자, 주사위 결과, 턴 번호 등)는 절대 그대로 드러내지 마세요 "
    "— 변화와 상처는 오직 서사적 묘사(예: \"반쯤 탈진한 채로\", \"무거운 상처를 안고\")로 전합니다."
)

# ---------------------------------------------------------------------------
# Onboarding acknowledgments (keyed by the beat JUST answered)
# Only the three beats that have a NEXT question receive an ack.
# ---------------------------------------------------------------------------

ONBOARDING_ACKS = {
    "name": "아, {answer}이라! 물 위로 외쳐 부르기 좋은 이름이군. 코악.",
    "concept": "호오… 그런 진흙에서 기어 나왔단 말이지. 무사 여신도 솔깃하시겠어.",
    "strengths": "빛에는 늘 진흙이 붙는 법이지 — 적어두마, 코악.",
}


def onboarding_ack(beat: str, answer: str) -> str:
    """The frog's reaction to the just-answered beat (empty string if none).
    Only the 'name' ack echoes the answer."""
    ack = ONBOARDING_ACKS.get(beat, "")
    return ack.format(answer=answer.strip()) if ("{answer}" in ack) else ack


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pick_loading_line(phase: str, *, rng=_random_module) -> str:
    """Return a random loading message for *phase*, or '' if none apply.

    *rng* must expose a ``choice(seq)`` method; the default is the ``random``
    module itself so callers get real randomness with no extra import.
    Tests inject a fake rng to get deterministic output.
    """
    pool = LOADING_POOLS.get(phase)
    if not pool:
        return ""
    return rng.choice(pool)


def epilogue_body(
    game: "GameFiles",
    *,
    frog: bool = True,
    role=config.NARRATOR,
    complete=providers.complete,
) -> str:
    """Generate the epilogue prose body from *game*.state and *game*.log.

    Calls ``complete(role, system, prompt)`` exactly once with a combined
    system string (EPILOGUE_SYSTEM, plus FROG_SYSTEM when *frog* is True) and
    a prompt that embeds the full state and log markdown.  Returns the raw
    text from ``complete``.

    *frog* defaults to True so existing callers and tests remain unchanged.
    Pass ``frog=False`` when ``settings.frog_tone == "off"`` to suppress the
    persona framing from the generated body.
    """
    prompt = (
        "아래는 이번 여정의 최종 상태와 기록일지입니다. 이를 바탕으로 에필로그 본문을 써 주십시오.\n\n"
        f"## 상태 (state)\n{game.state}\n\n"
        f"## 일지 (log)\n{game.log}"
    )
    system = EPILOGUE_SYSTEM + ("\n\n" + FROG_SYSTEM if frog else "")
    return complete(role, system, prompt)
