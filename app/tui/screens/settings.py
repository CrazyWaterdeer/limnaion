"""The Settings screen: edit provider/model per role, narration length, theme,
frog-tone. Saves on every change; applies the theme live."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Input, Label, Select, Static

from app import settings as settings_mod
from app.settings import AVAILABLE_THEMES, Settings
from app.types import RoleConfig

_PROVIDER_OPTIONS = [("Claude 구독", "claude-subscription"), ("OpenRouter", "openrouter")]
_LENGTH_OPTIONS = [("짧게", "short"), ("보통", "medium"), ("길게", "long")]
_FROG_OPTIONS = [("입·퇴장만", "bookends"), ("항상", "always"), ("끄기", "off")]
_ROLES = (("narrator", "화자 (이야기)"), ("referee", "심판 (판정)"), ("scribe", "서기 (기록)"))


class SettingsScreen(Screen):
    BINDINGS = [Binding("escape", "close", "닫기", show=True)]

    DEFAULT_CSS = """
    SettingsScreen #settings-title { dock: top; height: 1; background: $panel;
        color: $accent; padding: 0 1; }
    SettingsScreen #settings-body { padding: 1 2; }
    SettingsScreen Label { margin-top: 1; color: $text-muted; }
    SettingsScreen Select { width: 48; }
    SettingsScreen Input { width: 48; }
    """

    def __init__(self, settings: Settings, *, save=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.settings = settings
        self._save = save or settings_mod.save_settings

    def compose(self) -> ComposeResult:
        yield Static("게임 설정", id="settings-title", markup=False)
        with VerticalScroll(id="settings-body"):
            for key, label in _ROLES:
                rc: RoleConfig = getattr(self.settings, key)
                yield Label(label)
                yield Select(list(_PROVIDER_OPTIONS), value=rc.provider,
                             allow_blank=False, id=f"{key}_provider")
                yield Select(settings_mod.model_options(rc.provider, rc.model), value=rc.model,
                             allow_blank=False, id=f"{key}_model")
            yield Label("서술 길이")
            yield Select(list(_LENGTH_OPTIONS), value=self.settings.narration_length,
                         allow_blank=False, id="narration_length")
            yield Label("테마")
            yield Select([(t, t) for t in AVAILABLE_THEMES], value=self.settings.theme,
                         allow_blank=False, id="theme")
            yield Label("개구리 톤")
            yield Select(list(_FROG_OPTIONS), value=self.settings.frog_tone,
                         allow_blank=False, id="frog_tone")
            yield Label("OpenRouter API 키 (OpenRouter 모델 사용 시)")
            yield Input(value=self.settings.openrouter_api_key, password=True,
                        placeholder="sk-or-...", id="openrouter_key")
        yield Footer()

    def action_close(self) -> None:
        self.dismiss()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "openrouter_key":
            return
        val = event.value
        if val == self.settings.openrouter_api_key:
            return
        self.settings.openrouter_api_key = val
        import os
        if val:
            os.environ["OPENROUTER_API_KEY"] = val
        self._save(self.settings)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is Select.NULL:
            return
        sid, val = event.select.id, event.value
        s = self.settings
        if sid == "narration_length":
            if val == s.narration_length:
                return
            s.narration_length = val
        elif sid == "theme":
            if val == s.theme:
                return
            s.theme = val
            self.app.theme = val
        elif sid == "frog_tone":
            if val == s.frog_tone:
                return
            s.frog_tone = val
        elif sid.endswith("_provider"):
            role = sid[: -len("_provider")]
            rc = getattr(s, role)
            if val == rc.provider:
                return
            default_model = settings_mod.models_for(val)[0][1]
            setattr(s, role, RoleConfig(val, default_model))
            msel = self.query_one(f"#{role}_model", Select)
            msel.set_options(settings_mod.model_options(val, default_model))
            msel.value = default_model        # fires a model Changed; no-op vs the value we just set
        elif sid.endswith("_model"):
            role = sid[: -len("_model")]
            rc = getattr(s, role)
            if val == rc.model:
                return
            setattr(s, role, RoleConfig(rc.provider, val))
        else:
            return
        self._save(s)
