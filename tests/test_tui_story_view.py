"""StoryView.reset clears all mounted content and in-progress narration state."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Static

from app.tui.widgets.story_view import StoryView


class _Host(App):
    def compose(self) -> ComposeResult:
        yield StoryView(id="story")


async def test_reset_clears_children_and_active():
    app = _Host()
    async with app.run_test() as pilot:
        sv = app.query_one(StoryView)
        await sv.add_player_echo("행동 하나")
        await sv.begin_narration()
        sv.append_narration("서술 일부")
        await pilot.pause()
        assert len(sv.query(Static)) >= 2

        await sv.reset()
        await pilot.pause()
        assert len(sv.query(Static)) == 0        # everything removed
        assert sv.current_text == ""             # narration buffer cleared
        # a fresh turn works after reset (no dangling _active)
        await sv.add_player_echo("새 행동")
        await pilot.pause()
        assert len(sv.query(Static)) == 1
