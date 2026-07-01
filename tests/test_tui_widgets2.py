from textual.app import App, ComposeResult
from textual.widgets import Static

from app.tui.widgets.game_input import GameInput
from app.tui.widgets.status_panel import StatusPanel
from app.types import GameFiles

STATE = """# Current State
- **Scene:** A narrowing corridor.
- **Location:** The Eastern Passage
- **Condition:** HP 4/10
- **Inventory:** longsword
- **Active Objectives:**
  - [ ] Find the bounty
- **Last turn #:** 7"""

CHARACTER = """# Character: Kael
## Concept
A scarred mercenary.
## Attributes  (hidden)
- **Might** +2
## Specialties
- Swordplay
## Notes
HP max = 8 + Might.
"""

WORLD = "# World: The Iron Door"


def _game():
    return GameFiles(slug="demo", engine="", rules="", character=CHARACTER,
                     world=WORLD, state=STATE, log="")


class _PanelHost(App):
    def __init__(self):
        super().__init__()
        self.game = _game()

    def compose(self) -> ComposeResult:
        yield StatusPanel(self.game, id="status")


async def test_status_panel_state_then_character_no_numbers():
    app = _PanelHost()
    async with app.run_test() as pilot:
        panel = app.query_one(StatusPanel)
        await pilot.pause()
        body = app.query_one("#status-body", Static).content
        assert "부상" in body          # HP 4/10 -> worded
        assert "4/10" not in body      # raw HP hidden
        assert "Find the bounty" in body
        panel.toggle_character()
        await pilot.pause()
        body = app.query_one("#status-body", Static).content
        assert "Swordplay" in body
        assert "Might" not in body
        assert "+2" not in body
        assert "HP max" not in body


class _InputHost(App):
    def compose(self) -> ComposeResult:
        yield GameInput(id="input")


async def test_game_input_history_walk():
    app = _InputHost()
    async with app.run_test() as pilot:
        inp = app.query_one(GameInput)
        await pilot.pause()
        inp.remember("first")
        inp.remember("second")
        inp.action_history_prev()
        await pilot.pause()
        assert inp.value == "second"
        inp.action_history_prev()
        await pilot.pause()
        assert inp.value == "first"
        inp.action_history_next()
        await pilot.pause()
        assert inp.value == "second"
        inp.action_history_next()
        await pilot.pause()
        assert inp.value == ""  # walked past newest -> live edit (empty)


async def test_game_input_dedups_consecutive():
    app = _InputHost()
    async with app.run_test() as pilot:
        inp = app.query_one(GameInput)
        await pilot.pause()
        inp.remember("same")
        inp.remember("same")
        inp.action_history_prev()
        await pilot.pause()
        assert inp.value == "same"
        inp.action_history_prev()
        await pilot.pause()
        assert inp.value == "same"  # only one entry stored


# A1 — markup crash test: bracketed/[/]-containing field values must not crash
# the panel and must appear verbatim in the body (markup=False on #status-body).
_STATE_BRACKETED = (
    "# Current State\n"
    "- **Scene:** The gate is open.\n"
    "- **Inventory:** [runed] blade\n"
    "- **Condition:** HP 8/8\n"
    "- **Active Objectives:**\n"
    "  - [ ] Find the exit\n"
)


class _BracketPanelHost(App):
    def __init__(self, game):
        super().__init__()
        self._test_game = game

    def compose(self) -> ComposeResult:
        yield StatusPanel(self._test_game, id="status")


async def test_status_panel_bracket_no_crash_and_visible():
    # [runed] and [/] in field values must not raise MarkupError or vanish.
    game = GameFiles(slug="demo", engine="", rules="", character=CHARACTER,
                     world=WORLD, state=_STATE_BRACKETED, log="")
    app = _BracketPanelHost(game)
    async with app.run_test() as pilot:
        panel = app.query_one(StatusPanel)
        await pilot.pause()
        # refresh_from with bracketed content must not raise
        panel.refresh_from(game)
        await pilot.pause()
        body = app.query_one("#status-body", Static).content
        assert "[runed] blade" in body


# --- FIX 5: action notation *행동* (single asterisk, not double) ---

async def test_game_input_placeholder_uses_single_asterisk_notation():
    """GameInput placeholder must use *행동* (italic), not **행동** (bold)."""
    app = _InputHost()
    async with app.run_test() as pilot:
        await pilot.pause()
        inp = app.query_one(GameInput)
        assert "*행동*" in inp.placeholder
        assert "**행동**" not in inp.placeholder
