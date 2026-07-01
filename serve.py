"""Serve the Limnaion TUI over the web (textual-serve). Local: open http://localhost:8000

Set LIMNAION_SERVE_CMD to the command that launches the TUI in your environment.
For a pip/pipx install the default works; for a dev checkout use e.g.
`uv run --project /path/to/your/uv-env python -m app.main tui`.
"""
import os

from textual_serve.server import Server

COMMAND = os.environ.get("LIMNAION_SERVE_CMD", "python -m app.main tui")

Server(COMMAND, host="0.0.0.0", port=8000).serve()
