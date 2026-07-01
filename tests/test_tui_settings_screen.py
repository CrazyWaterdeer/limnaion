import os

from textual.app import App, ComposeResult
from textual.widgets import Input, Select

from app import config, settings as settings_mod
from app.settings import OPENROUTER_MODELS
from app.tui.screens.settings import SettingsScreen


class _Host(App):
    def __init__(self, screen):
        super().__init__()
        self._screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._screen)


async def test_theme_change_applies_live_and_saves():
    s = settings_mod.default_settings()
    saves = []
    screen = SettingsScreen(s, save=lambda x: saves.append(x.theme))
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        sel = screen.query_one("#theme", Select)
        screen.on_select_changed(Select.Changed(sel, "dracula"))
        await pilot.pause()
        assert s.theme == "dracula"
        assert app.theme == "dracula"      # applied live
        assert saves and saves[-1] == "dracula"


async def test_narration_length_change_saves():
    s = settings_mod.default_settings()
    saves = []
    screen = SettingsScreen(s, save=lambda x: saves.append(x.narration_length))
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        sel = screen.query_one("#narration_length", Select)
        screen.on_select_changed(Select.Changed(sel, "long"))
        await pilot.pause()
        assert s.narration_length == "long"
        assert saves[-1] == "long"


async def test_role_provider_and_model_change_saves():
    """Provider and model Select both update settings and save."""
    s = settings_mod.default_settings()
    saves = []
    screen = SettingsScreen(s, save=lambda x: saves.append((x.narrator.provider, x.narrator.model)))
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Change model via Select to a curated Claude value.
        model_sel = screen.query_one("#narrator_model", Select)
        screen.on_select_changed(Select.Changed(model_sel, config.CLAUDE_SONNET))
        await pilot.pause()
        assert s.narrator.model == config.CLAUDE_SONNET
        assert saves[-1] == ("claude-subscription", config.CLAUDE_SONNET)


async def test_provider_change_repopulates_model_and_resets_default():
    """Changing provider repopulates the model Select and resets model to new default."""
    s = settings_mod.default_settings()   # narrator starts at claude-subscription
    saves = []
    screen = SettingsScreen(s, save=lambda x: saves.append(x))
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        prov = screen.query_one("#narrator_provider", Select)
        screen.on_select_changed(Select.Changed(prov, "openrouter"))
        await pilot.pause()
        assert s.narrator.provider == "openrouter"
        assert s.narrator.model == OPENROUTER_MODELS[0][1]
        msel = screen.query_one("#narrator_model", Select)
        # Options must now match the openrouter curated list.
        actual_options = [(label, val) for label, val in msel._options]
        assert actual_options == settings_mod.models_for("openrouter")


def test_default_narrator_model_is_opus():
    """default_settings() narrator model must be CLAUDE_OPUS."""
    s = settings_mod.default_settings()
    assert s.narrator.model == config.CLAUDE_OPUS


async def test_escape_dismisses():
    s = settings_mod.default_settings()
    screen = SettingsScreen(s, save=lambda x: None)
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, SettingsScreen)


async def test_openrouter_key_input_updates_settings_and_env(monkeypatch):
    """Typing in the openrouter_key Input updates settings, saves, and sets env."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    s = settings_mod.default_settings()
    saves = []
    screen = SettingsScreen(s, save=lambda x: saves.append(x.openrouter_api_key))
    app = _Host(screen)
    async with app.run_test() as pilot:
        await pilot.pause()
        inp = screen.query_one("#openrouter_key", Input)
        screen.on_input_changed(Input.Changed(inp, "sk-or-testkey"))
        await pilot.pause()
        assert s.openrouter_api_key == "sk-or-testkey"
        assert saves and saves[-1] == "sk-or-testkey"
        assert os.environ.get("OPENROUTER_API_KEY") == "sk-or-testkey"
