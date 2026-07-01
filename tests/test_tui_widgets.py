from textual.app import App, ComposeResult
from textual.widgets import Static

from app.tui import messages
from app.tui.widgets.phase_line import PHASE_LABELS, PhaseLine
from app.tui.widgets.story_view import StoryView


def test_messages_carry_payload():
    assert messages.PhaseChanged("judge").phase == "judge"
    assert messages.NarrationChunk("자물쇠").text == "자물쇠"
    assert messages.TurnComplete("done").text == "done"
    assert messages.TurnFailed("boom").error == "boom"


class _StoryHost(App):
    def compose(self) -> ComposeResult:
        yield StoryView(id="sv")


async def test_story_view_streams_and_echoes():
    app = _StoryHost()
    async with app.run_test() as pilot:
        sv = app.query_one(StoryView)
        await sv.add_player_echo("**열어**")
        await sv.begin_narration()
        sv.append_narration("자물쇠가 ")
        sv.append_narration("열린다.")
        await pilot.pause()
        assert sv.current_text == "자물쇠가 열린다."
        blob = "\n".join(s.content for s in sv.query(Static))
        assert "**열어**" in blob
        assert "자물쇠가 열린다." in blob
        sv.end_narration("자물쇠가 열린다.")
        assert sv.current_text == ""


# ---------------------------------------------------------------------------
# Helpers shared by PhaseLine tests
# ---------------------------------------------------------------------------

class _FakeRng:
    """Deterministic RNG stub: always picks the first element of the sequence."""

    def choice(self, seq):
        return seq[0]


class _PhaseHost(App):
    def compose(self) -> ComposeResult:
        yield PhaseLine(id="pl")


# ---------------------------------------------------------------------------
# PhaseLine tests (replaces old test_phase_line_labels)
# ---------------------------------------------------------------------------

async def test_phase_line_loading_pool(monkeypatch):
    """Each active phase shows a string drawn from its LOADING_POOLS entry."""
    import app.tui.widgets.phase_line as phase_line_mod
    from app.persona import LOADING_POOLS

    monkeypatch.setattr(phase_line_mod, "_rng", _FakeRng())
    app = _PhaseHost()
    async with app.run_test() as pilot:
        pl = app.query_one(PhaseLine)
        for phase in ("judge", "dice", "narrate", "record"):
            pl.set_phase(phase)
            await pilot.pause()
            pool = LOADING_POOLS[phase]
            assert pl.content in pool, (
                f"phase={phase!r}: got {pl.content!r}, expected one of {pool}"
            )
            # With _FakeRng the result is always the first pool entry.
            assert pl.content == pool[0]


async def test_phase_line_idle_and_empty_show_blank(monkeypatch):
    """idle and '' phases always produce an empty content string."""
    import app.tui.widgets.phase_line as phase_line_mod

    monkeypatch.setattr(phase_line_mod, "_rng", _FakeRng())
    app = _PhaseHost()
    async with app.run_test() as pilot:
        pl = app.query_one(PhaseLine)
        pl.set_phase("idle")
        await pilot.pause()
        assert pl.content == ""
        pl.set_phase("")
        await pilot.pause()
        assert pl.content == ""


async def test_phase_line_fallback_to_phase_labels_when_pool_empty(monkeypatch):
    """When LOADING_POOLS[phase] is empty, PhaseLine falls back to PHASE_LABELS."""
    import app.tui.widgets.phase_line as phase_line_mod
    import app.persona as persona_mod

    empty_pools: dict[str, list[str]] = {k: [] for k in ("judge", "dice", "narrate", "record")}
    monkeypatch.setattr(persona_mod, "LOADING_POOLS", empty_pools)
    # B6: _rng monkeypatch removed — empty pools return "" before rng.choice is reached.

    app = _PhaseHost()
    async with app.run_test() as pilot:
        pl = app.query_one(PhaseLine)
        for phase in ("judge", "dice", "narrate", "record"):
            pl.set_phase(phase)
            await pilot.pause()
            assert pl.content == PHASE_LABELS[phase], (
                f"phase={phase!r}: expected fallback {PHASE_LABELS[phase]!r}, got {pl.content!r}"
            )
