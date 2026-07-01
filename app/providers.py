"""Provider-agnostic model backends.

Two providers back the engine's three roles (narrator, referee, scribe):
  - "claude-subscription": the `claude -p` CLI, authenticated via the claude.ai
    login (NOT pay-as-you-go API billing — ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN
    are stripped from the child env).
  - "openrouter": any OpenAI-compatible model over OpenRouter (added in a later task).

Everything here asserts wiring only; the CLI/SDK does the work. Tests mock
subprocess and the openai client, so nothing here touches the network. On
failure (non-zero exit, exception, or empty output) a call retries once and
then raises ModelError; callers degrade gracefully rather than crash.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Iterator

from app import config
from app.types import RoleConfig

try:  # optional dep: only needed for the OpenRouter provider
    import openai
except ImportError:  # pragma: no cover
    openai = None


class ModelError(Exception):
    """A model backend failed (non-zero exit, exception, or empty output)
    even after one automatic retry."""


def _retry(fn, attempts=2):
    """Call fn() up to `attempts` times (default: one initial call + one retry).

    Retries on ANY exception and on falsy/empty output. Returns the first
    successful, non-empty result. After the final attempt, raises ModelError
    (re-raising a ModelError from fn, otherwise wrapping the last exception).
    """
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            result = fn()
        except Exception as exc:  # any backend failure, including ModelError
            last_exc = exc
            print(f"[warn] backend call failed (attempt {i + 1}/{attempts}): {exc}", file=sys.stderr)
            continue
        if not result:
            last_exc = ModelError("model returned empty output")
            print(f"[warn] backend returned empty output (attempt {i + 1}/{attempts})", file=sys.stderr)
            continue
        return result
    if isinstance(last_exc, ModelError):
        raise last_exc
    raise ModelError(str(last_exc) if last_exc else "model call failed") from last_exc


def _claude_cwd() -> str:
    """Run claude -p OUTSIDE the project so it does not load the project's CLAUDE.md
    (which makes it adopt the TRPG-GM persona instead of just executing the prompt)."""
    d = Path(tempfile.gettempdir()) / "limnaion_claude_cwd"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def _claude_child_env() -> dict[str, str]:
    """Child env for `claude -p`. Two groups are stripped:

    - ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN — so the CLI uses the cached claude.ai
      OAuth login instead of pay-as-you-go API billing.
    - the parent Claude Code session vars (CLAUDE_CODE_*, CLAUDE_EFFORT,
      CLAUDE_PLUGIN_DATA). If they leak in, the child `claude -p` runs as a NESTED
      session — markedly slower and prone to agentic behaviour (asking clarifying
      questions instead of answering), which breaks the JSON contract and hits the
      timeout. Measured: stripping them cut a creator-sized call from ~60s to ~21s and
      turned a clarifying question into clean JSON. Only present when the app is itself
      launched from inside a Claude Code session; a harmless no-op otherwise.
    """
    drop = {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_EFFORT", "CLAUDE_PLUGIN_DATA"}
    return {
        k: v
        for k, v in os.environ.items()
        if k not in drop and not k.startswith("CLAUDE_CODE_")
    }


def claude_complete(model: str, system: str, prompt: str) -> str:
    def _once() -> str:
        # `claude -p` returns the model's raw reply on stdout. Do NOT pass
        # --output-format json: that wraps the reply in a CLI result envelope the
        # referee/scribe JSON parsers cannot read. The model is steered to emit JSON
        # via the system prompt, and those parsers strip any ```json fences, so
        # json_out needs no CLI flag here (it is a no-op for the claude backend).
        argv = ["claude", "-p", prompt, "--model", model]
        if system:
            argv += ["--append-system-prompt", system]
        result = subprocess.run(
            argv, capture_output=True, text=True, check=True,
            timeout=config.MODEL_TIMEOUT, env=_claude_child_env(),
            cwd=_claude_cwd(),
        )
        return result.stdout

    return _retry(_once)


def claude_stream(model: str, system: str, prompt: str) -> Iterator[str]:
    # stream-json REQUIRES --verbose or the CLI errors. The narration text arrives as
    # ONE complete block inside an `assistant` event (claude does not token-stream over
    # the CLI), so yielding once is expected and correct. Keep `proc` referenced for the
    # whole generator so GC does not close it mid-iteration.
    argv = [
        "claude", "-p", prompt, "--model", model,
        "--output-format", "stream-json", "--verbose",
    ]
    if system:
        argv += ["--append-system-prompt", system]
    proc = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, env=_claude_child_env(),
        cwd=_claude_cwd(),
    )
    timer = threading.Timer(config.MODEL_TIMEOUT, proc.kill)
    timer.start()
    yielded_any = False
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip non-JSON / partial lines
            if evt.get("type") == "assistant":
                for block in evt.get("message", {}).get("content", []):
                    if block.get("type") == "text" and block.get("text"):
                        yielded_any = True
                        yield block["text"]
    finally:
        timer.cancel()
        proc.wait()
    if proc.returncode not in (0, None) or not yielded_any:
        raise ModelError(
            f"claude stream failed (returncode={proc.returncode}, yielded={yielded_any})"
        )


def openrouter_complete(
    model: str, system: str, prompt: str, *, json_out: bool = False
) -> str:
    """One-shot completion via the OpenRouter (OpenAI-compatible) chat API.

    `json_out=True` asks the model for a JSON object via response_format. Retries
    once on any exception or empty output, then raises ModelError.
    """
    def _once() -> str:
        client = openai.OpenAI(
            base_url=config.OPENROUTER_BASE_URL,
            api_key=config.openrouter_api_key(),
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            **({"response_format": {"type": "json_object"}} if json_out else {}),
        )
        return resp.choices[0].message.content

    return _retry(_once)


def openrouter_stream(model: str, system: str, prompt: str) -> Iterator[str]:
    """Token-by-token streaming via the OpenRouter chat API.

    Keep BOTH the client and the stream referenced in THIS generator's scope for the
    whole iteration: a nested helper that returns the stream lets GC close the
    connection mid-iteration. Retry only the OPEN; once streaming we are committed and
    never retry mid-stream. Raises ModelError if the open fails, the stream errors
    mid-flight, or no content is produced.
    """
    last_exc: Exception | None = None
    client = None
    stream = None
    for attempt in range(2):
        try:
            client = openai.OpenAI(
                base_url=config.OPENROUTER_BASE_URL,
                api_key=config.openrouter_api_key(),
            )
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )
            break
        except Exception as exc:
            last_exc = exc
            print(
                f"[warn] openrouter stream open failed (attempt {attempt + 1}/2): {exc}",
                file=sys.stderr,
            )
    if stream is None:
        raise ModelError(
            str(last_exc) if last_exc else "openrouter stream failed to open"
        ) from last_exc

    yielded_any = False
    try:
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yielded_any = True
                yield delta
    except Exception as exc:
        raise ModelError(f"openrouter stream failed mid-stream: {exc}") from exc
    if not yielded_any:
        raise ModelError("openrouter stream produced no output")


def complete(role: RoleConfig, system: str, prompt: str, *, json_out: bool = False) -> str:
    """Run a one-shot completion for `role`, dispatching on `role.provider`.

    `json_out` is honored only by OpenRouter (sets response_format=json_object);
    it is a no-op for claude-subscription, where JSON is steered via the system
    prompt and `--output-format json` would corrupt the parser-facing stdout.
    """
    if role.provider == "claude-subscription":
        return claude_complete(role.model, system, prompt)
    elif role.provider == "openrouter":
        return openrouter_complete(role.model, system, prompt, json_out=json_out)
    raise ValueError(f"Unknown provider: {role.provider!r}")


def stream(role: RoleConfig, system: str, prompt: str) -> Iterator[str]:
    """Stream text chunks for `role`, dispatching on `role.provider`.

    Returns the backend generator directly (rather than `yield from`-ing it) so an
    unknown provider raises ValueError eagerly when stream() is called, and so the
    backend keeps its client/stream referenced for the whole iteration.
    """
    if role.provider == "claude-subscription":
        return claude_stream(role.model, system, prompt)
    elif role.provider == "openrouter":
        return openrouter_stream(role.model, system, prompt)
    raise ValueError(f"Unknown provider: {role.provider!r}")
