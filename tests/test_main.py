import sys

from app import main as main_module


def test_new_invokes_new_game_from_templates(monkeypatch):
    called = {}

    def fake_new(slug):
        called["slug"] = slug

    monkeypatch.setattr(
        main_module.game_files, "new_game_from_templates", fake_new
    )
    rc = main_module.main(["new", "demo"])
    assert rc == 0
    assert called["slug"] == "demo"


def test_play_invokes_run_repl(monkeypatch):
    called = {}

    def fake_repl(slug):
        called["slug"] = slug

    monkeypatch.setattr(main_module.orchestrator, "run_repl", fake_repl)
    rc = main_module.main(["play", "demo"])
    assert rc == 0
    assert called["slug"] == "demo"


def test_main_tui_invokes_run_play(monkeypatch):
    import app.tui.app as tui_app
    from app.main import main

    calls = []
    monkeypatch.setattr(tui_app, "run_play", lambda slug: calls.append(slug))
    rc = main(["tui", "demo"])
    assert rc == 0
    assert calls == ["demo"]


def test_main_tui_no_slug_routes_to_run_play(monkeypatch):
    import app.tui.app as tui_app
    from app.main import main

    calls = []
    monkeypatch.setattr(tui_app, "run_play", lambda slug=None: calls.append(slug))
    rc = main(["tui"])
    assert rc == 0
    assert calls == [None]


def test_limnaion_entrypoint_launches_splash_hub(monkeypatch):
    import app.tui.app as tui_app
    from app.main import limnaion

    calls = []
    monkeypatch.setattr(sys, "argv", ["limnaion"])
    monkeypatch.setattr(tui_app, "run_play", lambda slug=None: calls.append(slug))
    assert limnaion() is None
    assert calls == [None]


def test_limnaion_entrypoint_with_slug_jumps_to_game(monkeypatch):
    """limnaion <slug> must pass the slug through to run_play."""
    import app.tui.app as tui_app
    from app.main import limnaion

    calls = []
    monkeypatch.setattr(sys, "argv", ["limnaion", "demo"])
    monkeypatch.setattr(tui_app, "run_play", lambda slug=None: calls.append(slug))
    assert limnaion() is None
    assert calls == ["demo"]


def test_limnaion_entrypoint_no_slug_passes_none(monkeypatch):
    """limnaion with no argument must pass None to run_play."""
    import app.tui.app as tui_app
    from app.main import limnaion

    calls = []
    monkeypatch.setattr(sys, "argv", ["limnaion"])
    monkeypatch.setattr(tui_app, "run_play", lambda slug=None: calls.append(slug))
    limnaion()
    assert calls == [None]


def test_pyproject_declares_limnaion_distribution():
    import tomllib

    from app import config

    pyproject = config.FRAMEWORK_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    assert data["project"]["name"] == "limnaion"
    assert data["project"]["requires-python"] == ">=3.11"
    assert data["project"]["scripts"]["limnaion"] == "app.main:limnaion"
    assert data["build-system"]["build-backend"] == "hatchling.build"
    assert "app" in data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
