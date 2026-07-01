"""make_launcher.py -- Windows Desktop launcher installer.

Run once after installing Limnaion to create a Desktop shortcut.

Usage (from the repo root or any directory):
    python launcher/make_launcher.py

Behaviour on Windows:
  - If pywin32 (win32com.client) is importable: creates launcher/Limnaion.lnk
    on the Desktop, pointing to limnaion.bat with frog.ico as the icon.
  - If pywin32 is absent: copies limnaion.bat to the Desktop as a fallback.

Behaviour on Linux/macOS:
  - Imports cleanly (all Windows-specific calls are inside guarded blocks).
  - Calling main() raises RuntimeError with an explanatory message.
  - Intended only as a post-install step for Windows end-users.
"""
from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def bat_path() -> Path:
    """Absolute path to launcher/limnaion.bat."""
    return _HERE / "limnaion.bat"


def desktop_path() -> Path:
    """Best-effort path to the user's Desktop directory.

    Returns USERPROFILE/Desktop on Windows.  On Linux/macOS returns ~/Desktop
    (only reachable in tests that monkeypatch this function; main() raises
    before this is called on non-Windows systems).
    """
    if platform.system() == "Windows":
        import os  # noqa: PLC0415
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    return Path.home() / "Desktop"


def main() -> None:
    """Create a Desktop shortcut to limnaion.bat (Windows only).

    Raises:
        RuntimeError: when called on a non-Windows system.
        FileNotFoundError: when launcher/limnaion.bat is missing.
    """
    if platform.system() != "Windows":
        raise RuntimeError(
            "make_launcher.py is a Windows-only utility.  "
            "On Linux/macOS, launch Limnaion with: limnaion"
        )

    bat = bat_path()
    if not bat.exists():
        raise FileNotFoundError(f"Launcher script not found: {bat}")

    desk = desktop_path()
    desk.mkdir(parents=True, exist_ok=True)

    ico = _HERE / "frog.ico"
    shortcut_created = False

    # Attempt a proper .lnk shortcut via pywin32 (optional dependency).
    try:
        import win32com.client  # type: ignore[import-untyped]  # noqa: PLC0415
        shell = win32com.client.Dispatch("WScript.Shell")
        lnk = str(desk / "Limnaion.lnk")
        shortcut = shell.CreateShortCut(lnk)
        shortcut.TargetPath = str(bat)
        shortcut.WorkingDirectory = str(bat.parent)
        shortcut.Description = "Limnaion TRPG"
        if ico.exists():
            shortcut.IconLocation = str(ico)
        shortcut.save()
        shortcut_created = True
        print(f"Shortcut created: {lnk}")
    except Exception:  # noqa: BLE001
        # pywin32 not installed or COM call failed — fall through to copy.
        pass

    if not shortcut_created:
        dest = desk / bat.name
        shutil.copy2(bat, dest)
        print(f"Copied launcher to Desktop: {dest}")
        print("Tip: install pywin32 for a proper .lnk shortcut with icon.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"[make_launcher] {exc}", file=sys.stderr)
        sys.exit(1)
