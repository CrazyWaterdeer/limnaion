"""The Play screen: story view + status panel + phase line + input, wired to the
engine via a background thread worker."""
from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, Static

from app import snapshots
from app.orchestrator import Session, load_session
from app.settings import Settings, default_settings
from app.tui import projection
from app.tui.messages import NarrationChunk, PhaseChanged, TurnComplete, TurnFailed
from app.tui.runner import make_default_runner
from app.tui.screens.settings import SettingsScreen
from app.tui.widgets.game_input import GameInput
from app.tui.widgets.phase_line import PhaseLine
from app.tui.widgets.status_panel import StatusPanel
from app.tui.widgets.story_view import StoryView

HELP_TEXT = """Limnaion — 도움말

  Tab    상태 패널 열기/닫기
  F2     상태 / 캐릭터 / 등장인물 전환
  F1     이 도움말
  F3     설정 화면 열기
  ^Q     종료

입력 표기:
  *행동*     의도한 행동
  "대사"       말하기
  (ooc) 메모   설정·진행에 대한 메타 메모

아무 키나 눌러 닫기."""


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape,f1,q,space", "dismiss_help", "닫기")]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen #help-box { width: 56; height: auto; border: round $accent;
        padding: 1 2; background: $panel; }
    """

    def compose(self) -> ComposeResult:
        yield Static(HELP_TEXT, id="help-box", markup=False)

    def action_dismiss_help(self) -> None:
        self.dismiss()


class PlayScreen(Screen):
    BINDINGS = [
        Binding("tab", "toggle_status", "상태", show=True, priority=True),
        Binding("f2", "toggle_character", "보기", show=True),
        Binding("f1", "help", "도움말", show=True),
        Binding("f3", "settings", "설정", show=True),
        Binding("ctrl+e", "epilogue", "에필로그", show=True, priority=True),
        Binding("ctrl+b", "main_menu", "메인", show=True, priority=True),
        Binding("ctrl+z", "undo", "되돌리기", show=True, priority=True),
        Binding("ctrl+q", "quit", "종료", show=True, priority=True),
    ]

    DEFAULT_CSS = """
    PlayScreen #game-header { height: 1; background: $panel; color: $accent; padding: 0 1; }
    PlayScreen #main { height: 1fr; }
    PlayScreen StoryView { width: 1fr; }
    PlayScreen #phase-line { height: 1; color: $text-muted; padding: 0 1; }
    PlayScreen .recap-divider { color: $text-muted; text-align: center; margin: 1 0; }
    """

    def __init__(self, session: Session, *, settings: Settings | None = None,
                 runner=None, seed_from_transcript: bool = True, **kwargs) -> None:
        super().__init__(**kwargs)
        self.session = session
        self._settings = settings or default_settings()
        self._runner = runner or make_default_runner(settings=self._settings)
        self._turn_no = projection.turn_number(session.game)
        self._seed_from_transcript = seed_from_transcript
        self._pending_input = ""
        # Claude-Code-style queue: the input is never disabled. A submission made
        # while a turn is still running (incl. the post-narration 'record' scribe
        # step) is echoed as pending and run after the current turn finishes —
        # turns must stay sequential because each mutates the saved state.
        self._busy = False
        self._queue: list[str] = []
        # True only while on_input_submitted is mid-await (before _busy is set), so
        # a Ctrl+Z fired in that window can't undo out from under an in-flight submit.
        self._submitting = False

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="game-header", markup=False)
        with Horizontal(id="main"):
            yield StoryView(id="story")
            yield StatusPanel(self.session.game, id="status")
        yield PhaseLine(id="phase-line")
        yield GameInput(id="input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(GameInput).focus()
        if self._seed_from_transcript:
            self._seed_recent()

    def _seed_recent(self) -> None:
        from app.tui import transcript  # noqa: PLC0415 (local import to avoid cycle)
        recent = transcript.load_recent(self.session.slug, n=3)
        if not recent:
            return
        sv = self.query_one(StoryView)
        sv.mount(Static("─── 지난 이야기 ───", classes="recap-divider", markup=False))
        for player_input, narration in recent:
            if player_input:
                sv.mount(Static(f"{player_input}", classes="echo", markup=False))
            sv.mount(Static(narration, classes="narration", markup=False))
            self.session.recent.add(player_input or "(이어서)", narration)
        sv.scroll_end(animate=False)

    def _header_text(self) -> str:
        return f"{projection.game_title(self.session.game)} — 턴 {self._turn_no}"

    # --- bindings ---
    def action_toggle_status(self) -> None:
        self.query_one(StatusPanel).toggle_class("-hidden")

    def action_toggle_character(self) -> None:
        self.query_one(StatusPanel).cycle_view()

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_settings(self) -> None:
        self.app.push_screen(SettingsScreen(self._settings))

    def action_epilogue(self) -> None:
        from app.tui.screens.epilogue import EpilogueScreen  # noqa: PLC0415 (avoid import cycle)
        self.app.switch_screen(EpilogueScreen(self.session, settings=self._settings))

    def action_main_menu(self) -> None:
        from app.tui.screens.splash import SplashScreen  # noqa: PLC0415 (avoid import cycle)
        self.app.switch_screen(SplashScreen(settings=self._settings))

    async def action_undo(self) -> None:
        """Ctrl+Z: roll the game back one turn (repeatable, up to config.UNDO_SNAPSHOTS).
        Disabled while a turn runs or inputs are queued (turns must stay sequential)."""
        sv = self.query_one(StoryView)
        if self._busy or self._queue or self._submitting:
            await sv.show_note("(처리 중에는 되돌릴 수 없네. 코악.)")
            return
        if not snapshots.undo_available(self.session.slug):
            await sv.show_note("(더 되돌릴 게 없네. 코악.)")
            return
        try:
            snapshots.restore_latest(self.session.slug)
        except Exception as exc:  # noqa: BLE001 - a failed restore must not crash the UI
            await sv.show_note(f"(되돌리기에 실패했네. 코악. — {exc})")
            return  # snapshot left intact for a retry
        # reload the session from the restored files (fresh, empty recent buffer)
        self.session = load_session(self.session.slug)
        await self._rebuild_story()
        self._turn_no = projection.turn_number(self.session.game)
        self.query_one("#game-header", Static).update(self._header_text())
        self.query_one(StatusPanel).refresh_from(self.session.game)
        self.query_one(PhaseLine).set_phase("idle")
        self.query_one(GameInput).focus()

    async def _rebuild_story(self) -> None:
        """Clear the story view and re-seed it from the (now truncated) transcript,
        rebuilding the engine's recent-context buffer to match the restored state.
        self.session must already be the freshly reloaded session (empty recent)."""
        from app.tui import transcript  # noqa: PLC0415 (local import to avoid cycle)
        sv = self.query_one(StoryView)
        await sv.reset()
        recent = transcript.load_recent(self.session.slug, n=3)
        for player_input, narration in recent:
            if player_input:
                await sv.mount(Static(f"{player_input}", classes="echo", markup=False))
            await sv.mount(Static(narration, classes="narration", markup=False))
            self.session.recent.add(player_input or "(이어서)", narration)
        sv.scroll_end(animate=False)

    # --- input -> worker ---
    async def on_input_submitted(self, event: GameInput.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        # Mark submit-in-flight BEFORE the first await, so a Ctrl+Z dispatched while
        # we're suspended at add_player_echo can't undo before the turn even starts.
        self._submitting = True
        try:
            inp = self.query_one(GameInput)
            inp.remember(text)
            inp.value = ""
            await self.query_one(StoryView).add_player_echo(text)
            if self._busy:
                self._queue.append(text)  # a turn is running — run this one after it
            else:
                self._start_turn(text)
        finally:
            self._submitting = False

    def _start_turn(self, text: str) -> None:
        self._busy = True
        self._pending_input = text
        snapshots.snapshot_turn(self.session.slug)   # capture pre-turn state for undo
        self.run_turn(text)

    def _drain_queue(self) -> None:
        """Start the next queued turn, if any. Called when a turn finishes."""
        if self._queue and not self._busy:
            self._start_turn(self._queue.pop(0))

    @work(thread=True, exclusive=True)
    def run_turn(self, player_input: str) -> None:
        try:
            text = self._runner(
                self.session, player_input,
                on_phase=lambda p: self.post_message(PhaseChanged(p)),
                on_chunk=lambda c: self.post_message(NarrationChunk(c)),
            )
            self.post_message(TurnComplete(text))
        except Exception as exc:  # noqa: BLE001 - surface any turn failure to the player
            self.post_message(TurnFailed(str(exc)))

    # --- message handlers (UI thread) ---
    async def on_phase_changed(self, m: PhaseChanged) -> None:
        self.query_one(PhaseLine).set_phase(m.phase)
        if m.phase == "narrate":
            await self.query_one(StoryView).begin_narration()

    def on_narration_chunk(self, m: NarrationChunk) -> None:
        self.query_one(StoryView).append_narration(m.text)

    def on_turn_complete(self, m: TurnComplete) -> None:
        from app.tui import transcript  # noqa: PLC0415 (local import to avoid cycle)
        self.query_one(StoryView).end_narration(m.text)
        self.query_one(PhaseLine).set_phase("idle")
        self._turn_no = projection.turn_number(self.session.game)
        self.query_one("#game-header", Static).update(self._header_text())
        self.query_one(StatusPanel).refresh_from(self.session.game)
        transcript.append_turn(self.session.slug, self._pending_input, m.text)
        self._busy = False
        self._drain_queue()  # run the next queued input, if the player typed ahead
        self.query_one(GameInput).focus()

    async def on_turn_failed(self, m: TurnFailed) -> None:
        await self.query_one(StoryView).show_note(f"(이번 턴 처리에 실패했습니다: {m.error})")
        self.query_one(PhaseLine).set_phase("idle")
        self._busy = False
        self._drain_queue()  # a failed turn didn't mutate state; run any queued input
        self.query_one(GameInput).focus()
