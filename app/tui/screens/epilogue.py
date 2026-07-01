"""The Epilogue screen: Brekekos closes the tale.

On mount, composes the closing prose on a background thread worker
(persona.epilogue_body by default), then renders EPILOGUE_OPEN + body +
EPILOGUE_CLOSE in a scrollable view. Escape or Enter returns to the SplashScreen.
"""
from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Static

from app import persona
from app.orchestrator import Session
from app.settings import Settings, default_settings
from app.tui.messages import EpilogueFailed, EpilogueReady


class EpilogueScreen(Screen):
    BINDINGS = [Binding("escape,enter", "close", "닫기", show=True)]

    DEFAULT_CSS = """
    EpilogueScreen #epilogue-scroll { padding: 1 2; }
    EpilogueScreen .open { color: $accent; margin-bottom: 1; }
    EpilogueScreen .body { margin-bottom: 1; }
    EpilogueScreen .close { color: $accent; margin-top: 1; }
    """

    def __init__(self, session: Session, *, settings: Settings | None = None,
                 compose_body=persona.epilogue_body, **kwargs) -> None:
        super().__init__(**kwargs)
        self.session = session
        self._settings = settings or default_settings()
        self._compose_body = compose_body

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="epilogue-scroll"):
            yield Static(persona.EPILOGUE_OPEN, classes="open", markup=False)
            yield Static("개굴 — 이야기의 끝을 길어 올리는 중…", id="epilogue-body",
                         classes="body", markup=False)
            yield Static("", id="epilogue-close", classes="close", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self._start_body_worker()

    @work(thread=True, exclusive=True)
    def _start_body_worker(self) -> None:
        """Fetch the epilogue body prose on a background thread."""
        try:
            body = self._compose_body(
                self.session.game,
                frog=(self._settings.frog_tone != "off"),
            )
            self.post_message(EpilogueReady(body))
        except Exception as exc:  # noqa: BLE001 - surface any failure as a closing note
            self.post_message(EpilogueFailed(str(exc)))

    def on_epilogue_ready(self, m: EpilogueReady) -> None:
        self.query_one("#epilogue-body", Static).update(m.body)
        self.query_one("#epilogue-close", Static).update(persona.EPILOGUE_CLOSE)

    def on_epilogue_failed(self, m: EpilogueFailed) -> None:
        self.query_one("#epilogue-body", Static).update(
            f"(에필로그를 길어 올리지 못했습니다: {m.error})"
        )
        self.query_one("#epilogue-close", Static).update(persona.EPILOGUE_CLOSE)

    def action_close(self) -> None:
        from app.tui.screens.splash import SplashScreen  # lazy: avoid play<->splash cycle
        self.app.switch_screen(SplashScreen(settings=self._settings))
