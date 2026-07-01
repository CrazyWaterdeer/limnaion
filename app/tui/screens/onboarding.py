"""The Onboarding screen: a short frog-voiced Q&A that collects the player's
character, scaffolds a new game on a worker thread, then crosses over into the
Play screen with the opening scene seeded as the first narration block."""
from __future__ import annotations

import re

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Input, Static

from app import config, onboarding, persona
from app.orchestrator import load_session
from app.settings import Settings, default_settings
from app.tui.screens.play import PlayScreen
from app.tui.widgets.story_view import StoryView

# The ordered, input-collecting beats. "opening" is a preamble shown beside the
# first prompt, NOT a collected field. Two beats are DOUBLE beats, split by
# _split_pair on the first " / ":
#   name      -> inputs.name
#   concept   -> inputs.concept   / inputs.background
#   strengths -> inputs.strengths / inputs.weaknesses
#   scene     -> inputs.scene
_BEAT_ORDER = ("name", "concept", "strengths", "scene")
_WORKING_TEXT = "개구리가 네 이야기를 늪의 진흙으로 빚는 중…"


def _slugify(name: str) -> str:
    """ASCII slug from a character name; safe fallback for non-ASCII names."""
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "game"


def _unique_slug(base: str) -> str:
    """First slug of the form base, base-2, base-3, … whose game dir is free."""
    slug, n = base, 2
    while config.game_dir(slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def _split_pair(answer: str) -> tuple[str, str]:
    """Split one combined beat answer into (primary, secondary) on the first
    ' / '. Without the separator the whole answer is the primary and the
    secondary is empty. Fully deterministic — no model involved."""
    if " / " in answer:
        primary, secondary = answer.split(" / ", 1)
        return primary.strip(), secondary.strip()
    return answer.strip(), ""


class OnboardingCreated(Message):
    """The creator finished: a new game `slug` exists; `opening_scene` is prose."""

    def __init__(self, slug: str, opening_scene: str) -> None:
        self.slug = slug
        self.opening_scene = opening_scene
        super().__init__()


class OnboardingFailed(Message):
    """The creator raised; `error` is a short message for the player."""

    def __init__(self, error: str) -> None:
        self.error = error
        super().__init__()


class OnboardingScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "취소", show=True)]

    DEFAULT_CSS = """
    OnboardingScreen #onboarding-title { dock: top; height: 1; background: $panel;
        color: $accent; padding: 0 1; }
    OnboardingScreen #beat { padding: 1 2; height: 1fr; }
    OnboardingScreen Input { width: 1fr; margin: 0 2 1 2; }
    """

    def __init__(self, *, settings: Settings | None = None,
                 create=onboarding.create_game, **kwargs) -> None:
        super().__init__(**kwargs)
        self._settings = settings or default_settings()
        self._create = create
        self._index = 0
        self._raw: dict[str, str] = {}
        self._done = False
        self._slug: str | None = None   # derived once; reused on a failure retry

    def compose(self) -> ComposeResult:
        yield Static("새 게임 — 개구리의 문답", id="onboarding-title", markup=False)
        yield Static(self._prompt_for(0), id="beat", markup=False)
        yield Input(id="beat-input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#beat-input", Input).focus()

    def _prompt_for(self, index: int) -> str:
        text = persona.ONBOARDING_BEATS[_BEAT_ORDER[index]]
        if index == 0:
            return persona.ONBOARDING_BEATS["opening"] + "\n\n" + text
        return text

    def _assemble(self) -> onboarding.OnboardingInputs:
        concept, background = _split_pair(self._raw["concept"])
        strengths, weaknesses = _split_pair(self._raw["strengths"])
        return onboarding.OnboardingInputs(
            name=self._raw["name"],
            concept=concept,
            background=background,
            strengths=strengths,
            weaknesses=weaknesses,
            scene=self._raw["scene"],
        )

    # --- input -> beat walk ---
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._done:
            return
        answer = event.value.strip()
        if not answer:
            return
        inp = self.query_one("#beat-input", Input)
        inp.value = ""
        self._raw[_BEAT_ORDER[self._index]] = answer
        just = _BEAT_ORDER[self._index]
        self._index += 1
        if self._index < len(_BEAT_ORDER):
            ack = persona.onboarding_ack(just, answer)
            text = self._prompt_for(self._index)
            self.query_one("#beat", Static).update(f"{ack}\n\n{text}" if ack else text)
            return
        # All beats collected -> scaffold the game on a worker thread.
        self._done = True
        inp.disabled = True
        self.query_one("#beat", Static).update(_WORKING_TEXT)
        # Derive the slug once and reuse it on a retry, so a failure + re-submit
        # reuses the same game dir instead of orphaning it under a shifted slug.
        if self._slug is None:
            self._slug = _unique_slug(_slugify(self._raw["name"]))
        self._run_create(self._slug, self._assemble())

    @work(thread=True, exclusive=True)
    def _run_create(self, slug: str, inputs: onboarding.OnboardingInputs) -> None:
        try:
            opening = self._create(slug, inputs)
            self.post_message(OnboardingCreated(slug, opening))
        except Exception as exc:  # noqa: BLE001 - surface any creation failure
            self.post_message(OnboardingFailed(str(exc)))

    # --- worker -> UI ---
    def on_onboarding_created(self, m: OnboardingCreated) -> None:
        from app.tui import transcript  # noqa: PLC0415 (local import to avoid cycle)
        session = load_session(m.slug)
        # Seed the opening prose into engine memory so turn 1 has context.
        session.recent.add("(opening)", m.opening_scene)
        # Persist the opening to the transcript so a later resume can show it.
        transcript.append_turn(m.slug, "", m.opening_scene)
        # seed_from_transcript=False: onboarding seeds the crossing + opening via
        # _seed_opening; Play must NOT also seed from the transcript on a fresh game.
        play = PlayScreen(session, settings=self._settings, seed_from_transcript=False)
        self.app.switch_screen(play)
        # Seed after the Play screen's first refresh so StoryView is mounted.
        play.call_after_refresh(self._seed_opening, play, m.opening_scene)

    def _seed_opening(self, play: PlayScreen, opening_scene: str) -> None:
        """Mount the crossing transition then the opening scene into the StoryView."""
        sv = play.query_one(StoryView)
        sv.mount(Static(persona.CROSSING_TRANSITION, classes="narration", markup=False))
        sv.mount(Static(opening_scene, classes="narration", markup=False))

    def on_onboarding_failed(self, m: OnboardingFailed) -> None:
        self._done = False
        self._index = len(_BEAT_ORDER) - 1            # re-collect the last (scene) beat
        self.query_one("#beat", Static).update(
            f"개구리가 멈칫한다 — 다시 들려줘. ({m.error})"
        )
        inp = self.query_one("#beat-input", Input)
        inp.disabled = False
        inp.focus()

    def action_cancel(self) -> None:
        from app.tui.screens.splash import SplashScreen  # noqa: PLC0415 (avoid import cycle)
        self.app.switch_screen(SplashScreen(settings=self._settings))
