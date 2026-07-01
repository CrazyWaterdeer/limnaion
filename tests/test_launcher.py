"""Linux smoke tests for the Task 5 launcher files.

IMPORTANT — scope of these tests:
  These tests do NOT verify that the launcher opens Windows Terminal, creates a
  Windows Desktop shortcut, or runs on Windows in any way.  They verify only:
    1. make_launcher.py imports cleanly on Linux (all win32 APIs are guarded).
    2. launcher/limnaion.bat exists, is non-empty, and references "limnaion".
    3. launcher/frog.ico is a valid image file that Pillow can decode.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

LAUNCHER_DIR = Path(__file__).resolve().parent.parent / "launcher"


def test_make_launcher_imports_cleanly_on_linux():
    """Importing make_launcher on Linux must not raise, despite win32 references."""
    sys.modules.pop("make_launcher", None)
    sys.path.insert(0, str(LAUNCHER_DIR))
    try:
        mod = importlib.import_module("make_launcher")
        assert callable(getattr(mod, "main", None)), \
            "make_launcher must expose a callable main()"
        assert callable(getattr(mod, "bat_path", None)), \
            "make_launcher must expose bat_path()"
        assert callable(getattr(mod, "desktop_path", None)), \
            "make_launcher must expose desktop_path()"
    finally:
        sys.path.pop(0)
        sys.modules.pop("make_launcher", None)


def test_bat_exists_and_nonempty():
    bat = LAUNCHER_DIR / "limnaion.bat"
    assert bat.exists(), "launcher/limnaion.bat must exist"
    content = bat.read_text(encoding="utf-8", errors="replace")
    assert len(content.strip()) > 0, "limnaion.bat must not be empty"
    assert "limnaion" in content.lower(), \
        "limnaion.bat must reference the 'limnaion' command"


def test_frog_ico_is_valid_image():
    """frog.ico must be decodable by Pillow as a valid image."""
    Image = pytest.importorskip("PIL.Image")
    ico = LAUNCHER_DIR / "frog.ico"
    assert ico.exists(), "launcher/frog.ico must exist"
    img = Image.open(ico)
    img.load()  # forces full decode; raises on corrupt/truncated data
    assert img.width > 0 and img.height > 0, \
        f"frog.ico reports invalid dimensions: {img.width}x{img.height}"
