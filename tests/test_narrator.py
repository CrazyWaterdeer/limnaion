from app import config
from app.narrator import NARRATION_SYSTEM, build_prompt, narrate
from app.types import NarrationRequest


def _req(**overrides) -> NarrationRequest:
    base = dict(
        narration_rules="visibility: hidden. Render harm as sensation.",
        recent_turns_raw=[
            "P: **look around** | GM: the cold hall stretches empty, a torch guttering.",
            "P: anyone there? | GM: only your own breath answers in the dark.",
        ],
        compact_state="Scene: stone hall, north door. Time: deep night. Door is barred from your side.",
        player_input="**heave the north door open**",
        committed_outcome="the bar gives with a shriek; the door grinds wide and cold air pours in",
        visibility="hidden",
    )
    base.update(overrides)
    return NarrationRequest(**base)


def test_build_prompt_includes_state_recent_input_and_outcome():
    req = _req()
    prompt = build_prompt(req)
    assert req.compact_state in prompt
    for line in req.recent_turns_raw:
        assert line in prompt
    assert req.player_input in prompt
    assert req.committed_outcome in prompt
    # the committed-outcome instruction header is present when an outcome is given
    assert "Committed outcome" in prompt


def test_build_prompt_omits_outcome_section_when_none():
    req = _req(committed_outcome=None)
    prompt = build_prompt(req)
    # state, recent and input still present...
    assert req.compact_state in prompt
    assert req.player_input in prompt
    for line in req.recent_turns_raw:
        assert line in prompt
    # ...but no committed-outcome instruction at all
    assert "Committed outcome" not in prompt


def test_narration_system_is_korean_and_hides_numbers():
    # sanity: the system prompt is the Korean GM voice and forbids exposing mechanics
    assert "한국어" in NARRATION_SYSTEM
    assert "숫자" in NARRATION_SYSTEM  # "never reveal numbers"
    assert "선택지 메뉴를 절대 제시하지 마세요" in NARRATION_SYSTEM  # no choice menus
    assert "캐릭터의 내면이나 선택을 대신 쓰지 마세요" in NARRATION_SYSTEM  # don't author character


def test_narrate_streams_and_joins_chunks():
    chunks = ["차가운 공기가 ", "복도로 ", "쏟아져 ", "들어온다."]
    captured = {}

    def fake_stream(role, system, prompt):
        captured["role"] = role
        captured["system"] = system
        captured["prompt"] = prompt
        yield from chunks

    out = list(narrate(_req(), stream=fake_stream))
    assert out == chunks
    assert "".join(out) == "차가운 공기가 복도로 쏟아져 들어온다."
    # narrate wires the role + static system prompt + built per-turn prompt through
    assert captured["role"] == config.NARRATOR
    assert captured["system"] == NARRATION_SYSTEM
    assert _req().player_input in captured["prompt"]


def test_narrate_medium_length_leaves_system_unchanged():
    captured = {}

    def fake_stream(role, system, prompt):
        captured["system"] = system
        return iter(["x"])

    list(narrate(_req(), stream=fake_stream, length="medium"))
    assert captured["system"] == NARRATION_SYSTEM   # no-op for medium


def test_narrate_short_and_long_append_directive():
    seen = {}

    def fake_stream(role, system, prompt):
        seen["system"] = system
        return iter(["x"])

    list(narrate(_req(), stream=fake_stream, length="short"))
    assert NARRATION_SYSTEM in seen["system"] and seen["system"] != NARRATION_SYSTEM
    short_sys = seen["system"]
    list(narrate(_req(), stream=fake_stream, length="long"))
    assert seen["system"] != short_sys   # long differs from short
