"""Onboarding screen: a frog-voiced Q&A that assembles OnboardingInputs (with the
deterministic ' / ' double-beat split), scaffolds a game on a worker thread via an
injected creator, then crosses into PlayScreen with the opening scene seeded."""
from textual.app import App
from textual.widgets import Input, Static

from app import config, game_files, persona
from app.onboarding import OnboardingInputs
from app.tui.screens.onboarding import OnboardingScreen, _slugify, _unique_slug
from app.tui.screens.play import PlayScreen
from app.tui.widgets.story_view import StoryView


class _Host(App):
    """Minimal host that pushes the screen under test on mount."""

    def __init__(self, screen):
        super().__init__()
        self._screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._screen)


async def _submit(screen, value):
    """Drive a single beat by invoking the submit handler directly (deterministic)."""
    inp = screen.query_one("#beat-input", Input)
    await screen.on_input_submitted(Input.Submitted(inp, value))


async def test_onboarding_walks_beats_and_reaches_play(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    captured: dict = {}

    def fake_create(slug, inputs, role=None):
        # Mirror create_game's observable effect: a real game on disk + opening prose,
        # without any model call, so load_session(slug) works downstream.
        captured["slug"] = slug
        captured["inputs"] = inputs
        captured["role"] = role
        game_files.new_game_from_templates(slug)
        return "안개가 걷히고, 늪의 가장자리가 드러난다."

    screen = OnboardingScreen(create=fake_create)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        # The opening preamble is shown alongside the first (name) prompt.
        beat = screen.query_one("#beat", Static)
        assert persona.ONBOARDING_BEATS["opening"] in beat.content

        # Walk the four collected beats; the concept/strengths answers use ' / '.
        await _submit(screen, "Lyra")
        await _submit(screen, "물도둑 / 운하 빈민가 출신")        # concept / background
        await _submit(screen, "재빠른 손 / 깊은 물 공포")         # strengths / weaknesses
        await _submit(screen, "달빛 어린 부두에서 깨어난다")      # scene
        await app.workers.wait_for_complete()                     # B1: deterministic worker wait
        await pilot.pause()                                       # allow post-worker UI updates

        # OnboardingInputs assembled with the deterministic split.
        inputs = captured["inputs"]
        assert isinstance(inputs, OnboardingInputs)
        assert inputs.name == "Lyra"
        assert inputs.concept == "물도둑"
        assert inputs.background == "운하 빈민가 출신"
        assert inputs.strengths == "재빠른 손"
        assert inputs.weaknesses == "깊은 물 공포"
        assert inputs.scene == "달빛 어린 부두에서 깨어난다"

        # Slug derived from the name; the game was scaffolded on disk.
        assert captured["slug"] == "lyra"
        assert config.game_dir("lyra").exists()
        # Creation honors the configured scribe role (not the hardcoded Haiku default).
        assert captured["role"] == screen._settings.scribe

        # PlayScreen reached, opening scene seeded as the first narration block.
        assert isinstance(app.screen, PlayScreen)
        # NOTE: app.query_one() searches app.default_screen (the initial _default screen),
        # not pushed screens. We must query from app.screen (the active PlayScreen).
        sv = app.screen.query_one(StoryView)
        blob = "\n".join(s.content for s in sv.query(Static))
        # A1: crossing transition must be visible ahead of the opening scene.
        assert persona.CROSSING_TRANSITION in blob
        assert "안개가 걷히고" in blob


async def test_slugify_and_uniqueness(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    assert _slugify("Lyra the Bold!") == "lyra-the-bold"
    assert _slugify("개구리") == "game"            # non-ASCII collapses → safe fallback
    game_files.new_game_from_templates("lyra")
    assert _unique_slug("lyra") == "lyra-2"        # avoids the existing game dir
    assert _unique_slug("fresh") == "fresh"


async def test_onboarding_failure_retry_reuses_slug(tmp_path, monkeypatch):
    """B2: a create stub that raises on the first call and succeeds on the second.
    After the failure the input must be re-enabled and the beat must contain the
    error fragment.  On retry both calls must use the SAME slug, only ONE game
    dir may exist, and the app must reach PlayScreen.
    """
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    call_slugs: list[str] = []

    def fake_create(slug, inputs, role=None):
        call_slugs.append(slug)
        if len(call_slugs) == 1:
            raise RuntimeError("모델 오류")
        game_files.new_game_from_templates(slug)
        return "물안개가 걷혔다."

    screen = OnboardingScreen(create=fake_create)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Walk all four beats.
        await _submit(screen, "Kael")
        await _submit(screen, "검사 / 망명자")
        await _submit(screen, "검술 / 분노 조절 어려움")
        await _submit(screen, "폐허가 된 성채 앞에 선다")

        # First attempt fails.
        await app.workers.wait_for_complete()
        await pilot.pause()

        inp = screen.query_one("#beat-input", Input)
        assert not inp.disabled, "input must be re-enabled after failure"
        beat = screen.query_one("#beat", Static).content
        assert "모델 오류" in beat, f"error fragment missing in beat: {beat!r}"

        # Re-submit the last beat (scene) to retry creation.
        await _submit(screen, "폐허가 된 성채 앞에 선다")
        await app.workers.wait_for_complete()
        await pilot.pause()

        # Both calls must use the same slug.
        assert len(call_slugs) == 2
        assert call_slugs[0] == call_slugs[1], (
            f"slug changed between attempts: {call_slugs}"
        )
        # Exactly one game dir must exist.
        game_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
        assert len(game_dirs) == 1, f"expected 1 game dir, got {[d.name for d in game_dirs]}"
        # App must have transitioned to PlayScreen.
        assert isinstance(app.screen, PlayScreen)


async def test_name_ack_shown_before_concept_prompt(tmp_path, monkeypatch):
    """After submitting the name beat, the #beat Static must contain the echoed
    name ack AND the next (concept) prompt text."""
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    screen = OnboardingScreen(create=lambda slug, inputs, role=None: "")
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _submit(screen, "진")
        await pilot.pause()
        beat_content = screen.query_one("#beat", Static).content
        # Echoed name must appear in the ack.
        assert "진" in beat_content
        # Concept prompt text must follow the ack.
        assert persona.ONBOARDING_BEATS["concept"] in beat_content


def test_split_pair_is_deterministic():
    from app.tui.screens.onboarding import _split_pair
    assert _split_pair("재빠른 손 / 깊은 물 공포") == ("재빠른 손", "깊은 물 공포")
    assert _split_pair("a / b / c") == ("a", "b / c")   # split only on the FIRST ' / '
    assert _split_pair("외톨이") == ("외톨이", "")        # no separator → secondary empty
