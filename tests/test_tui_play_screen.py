from textual.widgets import Static

from app import config, game_files
from app import settings as settings_mod
from app.tui import projection
from app.tui import transcript
from app.tui.app import LimnaionApp
from app.tui.screens.play import HelpScreen, PlayScreen
from app.tui.screens.settings import SettingsScreen
from app.tui.screens.splash import SplashScreen
from app.tui.widgets.game_input import GameInput
from app.tui.widgets.phase_line import PhaseLine
from app.tui.widgets.status_panel import StatusPanel
from app.tui.widgets.story_view import StoryView


def _setup_game(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GAMES_DIR", tmp_path)
    slug = "testgame"
    game_files.new_game_from_templates(slug)
    return slug


def _fake_runner(session, player_input, *, on_phase, on_chunk):
    on_phase("judge")
    on_phase("dice")
    on_phase("narrate")
    on_chunk("자물쇠가 ")
    on_chunk("열린다.")
    on_phase("record")
    return "자물쇠가 열린다."


async def test_submit_drives_turn_and_streams(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)

    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        screen = app.screen
        assert isinstance(screen, PlayScreen)
        inp = app.query_one(GameInput)
        # Drive the submit handler directly for determinism.
        await screen.on_input_submitted(GameInput.Submitted(inp, "**pick the lock**"))
        await pilot.pause(0.3)

        sv = app.query_one(StoryView)
        blob = "\n".join(s.content for s in sv.query(Static))
        assert "**pick the lock**" in blob
        assert "자물쇠가 열린다." in blob
        # phase line returns to idle, input re-enabled, history remembered
        assert app.query_one(PhaseLine).content == ""
        assert inp.disabled is False
        inp.action_history_prev()
        assert inp.value == "**pick the lock**"
        # B1: status panel was refreshed after the turn (wiring coverage)
        status_body = app.query_one("#status-body", Static).content
        assert status_body  # non-empty
        assert "멀쩡함" in status_body  # Condition from template state through wound_band


async def test_input_queues_while_busy_and_drains(tmp_path, monkeypatch):
    """Claude-Code-style queue: submitting while a turn runs echoes the input as
    pending (input is never disabled) and runs it after the current turn ends."""
    slug = _setup_game(tmp_path, monkeypatch)
    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        screen = app.screen
        inp = app.query_one(GameInput)
        screen._busy = True  # pretend a turn is already in progress
        await screen.on_input_submitted(GameInput.Submitted(inp, "**문 옆에서 기다린다**"))
        await pilot.pause()
        blob = "\n".join(s.content for s in app.query_one(StoryView).query(Static))
        assert "**문 옆에서 기다린다**" in blob          # echoed immediately (pending)
        assert screen._queue == ["**문 옆에서 기다린다**"]  # queued, not started
        assert inp.disabled is False                       # input never disabled
        # finishing the current turn drains the queue and runs the pending input
        screen._busy = False
        screen._drain_queue()
        await pilot.pause(0.3)
        assert screen._queue == []      # drained
        assert screen._busy is False    # the queued turn ran to completion


async def test_tab_toggles_status_panel(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)

    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        panel = app.query_one(StatusPanel)
        assert not panel.has_class("-hidden")
        await pilot.press("tab")
        await pilot.pause()
        assert panel.has_class("-hidden")
        await pilot.press("tab")
        await pilot.pause()
        assert not panel.has_class("-hidden")


async def test_turn_failure_surfaces_message(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)


    def boom_runner(session, player_input, *, on_phase, on_chunk):
        on_phase("judge")
        raise RuntimeError("referee exploded")

    app = LimnaionApp(slug=slug, runner=boom_runner)
    async with app.run_test() as pilot:
        screen = app.screen
        assert isinstance(screen, PlayScreen)
        inp = app.query_one(GameInput)
        await screen.on_input_submitted(GameInput.Submitted(inp, "**do**"))
        await pilot.pause(0.3)
        sv = app.query_one(StoryView)
        blob = "\n".join(s.content for s in sv.query(Static))
        assert "실패" in blob
        assert inp.disabled is False


# C1 — binding coverage: empty input guard, F1 help, F2 character view

async def test_empty_input_ignored(tmp_path, monkeypatch):
    """Whitespace-only submission must not echo, not disable input, not run a turn."""
    slug = _setup_game(tmp_path, monkeypatch)

    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        screen = app.screen
        assert isinstance(screen, PlayScreen)
        inp = app.query_one(GameInput)
        await screen.on_input_submitted(GameInput.Submitted(inp, "   "))
        await pilot.pause()
        sv = app.query_one(StoryView)
        assert list(sv.query(Static)) == []   # no echo or narration
        assert inp.disabled is False           # runner never ran


async def test_f1_opens_and_closes_help(tmp_path, monkeypatch):
    """F1 pushes HelpScreen; Escape pops it back to PlayScreen."""
    slug = _setup_game(tmp_path, monkeypatch)

    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        await pilot.press("f1")
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, PlayScreen)


async def test_f2_switches_to_character_view(tmp_path, monkeypatch):
    """F2 toggles the status panel to character view; body contains character data."""
    slug = _setup_game(tmp_path, monkeypatch)

    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("f2")
        await pilot.pause()
        body = app.query_one("#status-body", Static).content
        # character_lines emits section headings from _CHAR_ALLOWED;
        # template character.md has an exact "## Concept" heading.
        assert body  # non-empty — character data is present
        assert "Concept" in body


async def test_app_applies_theme_from_settings(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)

    s = settings_mod.default_settings()
    s.theme = "dracula"
    app = LimnaionApp(slug=slug, settings=s, runner=_fake_runner)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.theme == "dracula"


async def test_f3_opens_settings_screen(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)

    app = LimnaionApp(slug=slug, settings=settings_mod.default_settings(), runner=_fake_runner)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("f3")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, PlayScreen)


async def test_playscreen_builds_runner_from_settings_when_none(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)

    s = settings_mod.default_settings()
    app = LimnaionApp(slug=slug, settings=s)          # no runner injected
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, PlayScreen)
        assert callable(screen._runner)              # a default runner was built from settings
        assert screen._runner.__name__ == "run"      # proves make_default_runner's inner closure


async def test_action_main_menu_switches_to_splash_screen(tmp_path, monkeypatch):
    """ctrl+b / action_main_menu must switch to SplashScreen; game state untouched."""
    slug = _setup_game(tmp_path, monkeypatch)

    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, PlayScreen)
        play = app.screen
        play.action_main_menu()
        await pilot.pause()
        assert isinstance(app.screen, SplashScreen)


async def test_turn_persisted_to_transcript(tmp_path, monkeypatch):
    """A completed turn is written to the per-game transcript JSONL."""
    slug = _setup_game(tmp_path, monkeypatch)

    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        screen = app.screen
        assert isinstance(screen, PlayScreen)
        inp = app.query_one(GameInput)
        await screen.on_input_submitted(GameInput.Submitted(inp, "**pick the lock**"))
        await pilot.pause(0.3)

        turns = transcript.load_recent(slug)
        assert len(turns) == 1
        player_text, narration = turns[0]
        assert player_text == "**pick the lock**"
        assert narration == "자물쇠가 열린다."


async def test_resume_seeds_storyview_and_narrator_context(tmp_path, monkeypatch):
    """On resume, the StoryView shows a recap divider + last narrations, and
    session.recent is repopulated so the narrator has context."""
    slug = _setup_game(tmp_path, monkeypatch)

    # Pre-populate the transcript with two turns (simulating a prior session).
    transcript.append_turn(slug, "문을 밀어본다", "문이 천천히 열린다.")
    transcript.append_turn(slug, "안으로 들어간다", "어둠 속에서 촛불 하나가 흔들린다.")

    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, PlayScreen)

        sv = screen.query_one(StoryView)
        blob = "\n".join(s.content for s in sv.query(Static))

        # Recap divider must be present.
        assert "─── 지난 이야기 ───" in blob
        # Last narration must appear.
        assert "어둠 속에서 촛불 하나가 흔들린다." in blob
        # First narration also present (n=3, both fit).
        assert "문이 천천히 열린다." in blob

        # Narrator context must be repopulated.
        assert len(screen.session.recent._turns) > 0


# C2b/C2c — F2 cycles state → character → npc → state

async def test_f2_cycles_three_views(tmp_path, monkeypatch):
    """F2 pressed three times cycles state → character → npc → state; NPC view shows cast."""
    slug = _setup_game(tmp_path, monkeypatch)
    # Write a world.md with a Key NPCs section so the npc view has data.
    from app import config as _cfg, game_files as _gf
    d = _cfg.game_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    (d / "world.md").write_text(
        "# 철문 너머의 빚\n\n## Key NPCs\n- **Mara** — the broker\n\n"
        "## Lore\n- Secret: the vault holds something terrible.\n",
        encoding="utf-8",
    )

    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Press 1: state → character
        await pilot.press("f2")
        await pilot.pause()
        body = app.query_one("#status-body", Static).content
        assert "Concept" in body, "after 1×F2 should show character view"

        # Press 2: character → npc
        await pilot.press("f2")
        await pilot.pause()
        body = app.query_one("#status-body", Static).content
        assert "Mara" in body, "after 2×F2 should show NPC view with Mara"
        assert "terrible" not in body, "GM lore must be hidden from NPC view"

        # Press 3: npc → state
        await pilot.press("f2")
        await pilot.pause()
        body = app.query_one("#status-body", Static).content
        assert "멀쩡함" in body, "after 3×F2 should be back to state view"


async def test_ctrl_z_undoes_last_turn(tmp_path, monkeypatch):
    """After a completed turn, action_undo restores the pre-turn state.md and
    transcript, rebuilds the story, and decrements the header turn number."""
    slug = _setup_game(tmp_path, monkeypatch)
    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        screen = app.screen
        inp = app.query_one(GameInput)
        state_before = (config.game_dir(slug) / "state.md").read_text(encoding="utf-8")

        await screen.on_input_submitted(GameInput.Submitted(inp, "**pick the lock**"))
        await pilot.pause(0.3)
        # the fake runner's scribe stand-in must have changed state.md; simulate it:
        (config.game_dir(slug) / "state.md").write_text("AFTER TURN", encoding="utf-8")

        assert screen._busy is False
        await screen.action_undo()
        await pilot.pause(0.3)

        # state.md rolled back to the pre-turn snapshot
        assert (config.game_dir(slug) / "state.md").read_text(encoding="utf-8") == state_before
        # the player echo from the undone turn is gone from the story
        blob = "\n".join(s.content for s in app.query_one(StoryView).query(Static))
        assert "**pick the lock**" not in blob


async def test_ctrl_z_noop_when_nothing_to_undo(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        screen = app.screen
        await screen.action_undo()               # no turn taken yet
        await pilot.pause()
        blob = "\n".join(s.content for s in app.query_one(StoryView).query(Static))
        assert "더 되돌릴" in blob                 # brief note, no crash


async def test_ctrl_z_ignored_while_busy(tmp_path, monkeypatch):
    slug = _setup_game(tmp_path, monkeypatch)
    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        screen = app.screen
        screen._busy = True                      # pretend a turn is running
        # snapshot one so undo_available would otherwise be True
        from app import snapshots
        snapshots.snapshot_turn(slug)
        (config.game_dir(slug) / "state.md").write_text("MID", encoding="utf-8")
        await screen.action_undo()
        await pilot.pause()
        # busy guard: state.md NOT restored
        assert (config.game_dir(slug) / "state.md").read_text(encoding="utf-8") == "MID"


async def test_ctrl_z_ignored_while_queued(tmp_path, monkeypatch):
    """The undo guard also blocks when a turn is queued but not yet running
    (_busy False, _queue non-empty) — turns pending in the queue must still run."""
    slug = _setup_game(tmp_path, monkeypatch)
    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        screen = app.screen
        from app import snapshots
        snapshots.snapshot_turn(slug)                 # undo_available() would be True
        (config.game_dir(slug) / "state.md").write_text("MID", encoding="utf-8")
        screen._busy = False
        screen._queue = ["**대기 중 입력**"]          # a turn is queued
        await screen.action_undo()
        await pilot.pause()
        # queue guard: state.md NOT restored, and the note is shown
        assert (config.game_dir(slug) / "state.md").read_text(encoding="utf-8") == "MID"
        blob = "\n".join(s.content for s in app.query_one(StoryView).query(Static))
        assert "처리 중" in blob


async def test_ctrl_z_ignored_while_submitting(tmp_path, monkeypatch):
    """Race guard: a Ctrl+Z dispatched while on_input_submitted is mid-await
    (_submitting True, _busy still False) must not undo out from under the submit."""
    slug = _setup_game(tmp_path, monkeypatch)
    app = LimnaionApp(slug=slug, runner=_fake_runner)
    async with app.run_test() as pilot:
        screen = app.screen
        from app import snapshots
        snapshots.snapshot_turn(slug)
        (config.game_dir(slug) / "state.md").write_text("MID", encoding="utf-8")
        screen._submitting = True                     # simulate mid-submit await
        await screen.action_undo()
        await pilot.pause()
        assert (config.game_dir(slug) / "state.md").read_text(encoding="utf-8") == "MID"
