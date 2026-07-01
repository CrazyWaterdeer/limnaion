from app import config, settings
from app.types import RoleConfig


def test_default_settings_from_config():
    s = settings.default_settings()
    assert s.narrator == config.NARRATOR
    assert s.referee == config.REFEREE
    assert s.scribe == config.SCRIBE
    assert s.narration_length == "medium"
    assert s.theme == settings.DEFAULT_THEME
    assert s.frog_tone == "bookends"


def test_toml_roundtrip():
    s = settings.default_settings()
    s.narrator = RoleConfig("openrouter", "google/gemini-2.5-flash")
    s.narration_length = "long"
    s.theme = "dracula"
    s.frog_tone = "off"
    back = settings.from_toml_dict(settings.to_toml_dict(s))
    assert back == s


def test_save_then_load(tmp_path):
    p = tmp_path / "settings.toml"
    s = settings.default_settings()
    s.referee = RoleConfig("openrouter", "anthropic/claude-3.5-sonnet")
    s.theme = "monokai"
    settings.save_settings(s, p)
    assert p.exists()
    loaded = settings.load_settings(p)
    assert loaded == s


def test_load_missing_file_returns_defaults(tmp_path):
    loaded = settings.load_settings(tmp_path / "nope.toml")
    assert loaded == settings.default_settings()


def test_partial_file_merges_over_defaults(tmp_path):
    p = tmp_path / "settings.toml"
    p.write_text('narration_length = "short"\n', encoding="utf-8")
    loaded = settings.load_settings(p)
    assert loaded.narration_length == "short"          # from file
    assert loaded.narrator == config.NARRATOR           # default preserved
    assert loaded.theme == settings.DEFAULT_THEME       # default preserved


def test_invalid_values_fall_back_per_field(tmp_path):
    p = tmp_path / "settings.toml"
    p.write_text(
        'narration_length = "epic"\n'
        'theme = "not-a-theme"\n'
        'frog_tone = "loud"\n'
        '[providers.narrator]\n'
        'provider = "telepathy"\n'
        'model = ""\n',
        encoding="utf-8",
    )
    loaded = settings.load_settings(p)
    d = settings.default_settings()
    assert loaded.narration_length == d.narration_length
    assert loaded.theme == d.theme
    assert loaded.frog_tone == d.frog_tone
    assert loaded.narrator == d.narrator   # bad provider + empty model -> default role


def test_malformed_toml_returns_defaults(tmp_path):
    p = tmp_path / "settings.toml"
    p.write_text("this is = = not toml [[[", encoding="utf-8")
    assert settings.load_settings(p) == settings.default_settings()


def test_settings_path_under_limnaion():
    assert settings.settings_path().name == "settings.toml"
    assert "limnaion" in str(settings.settings_path())


def test_non_dict_provider_section_falls_back(tmp_path):
    p = tmp_path / "settings.toml"
    p.write_text(
        '[providers]\nnarrator = "claude-subscription"\n',  # scalar, not a table
        encoding="utf-8",
    )
    loaded = settings.load_settings(p)          # must NOT raise
    assert loaded.narrator == settings.default_settings().narrator


def test_openrouter_api_key_default_is_empty():
    s = settings.default_settings()
    assert s.openrouter_api_key == ""


def test_openrouter_api_key_roundtrip(tmp_path):
    p = tmp_path / "settings.toml"
    s = settings.default_settings()
    s.openrouter_api_key = "sk-or-test-key"
    settings.save_settings(s, p)
    loaded = settings.load_settings(p)
    assert loaded.openrouter_api_key == "sk-or-test-key"


def test_openrouter_api_key_toml_roundtrip():
    s = settings.default_settings()
    s.openrouter_api_key = "sk-or-abc123"
    back = settings.from_toml_dict(settings.to_toml_dict(s))
    assert back.openrouter_api_key == "sk-or-abc123"
