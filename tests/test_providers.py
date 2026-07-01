from types import SimpleNamespace

import pytest

from app import config, providers


# ---- _retry -----------------------------------------------------------------

def test_retry_retries_once_then_raises_model_error(capsys):
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise RuntimeError("boom")

    with pytest.raises(providers.ModelError):
        providers._retry(always_fails)

    assert calls["n"] == 2  # one initial call + one retry
    err = capsys.readouterr().err
    assert "attempt 1/2" in err and "attempt 2/2" in err  # each failure logged to stderr


def test_retry_returns_first_nonempty_result(capsys):
    calls = {"n": 0}

    def empty_then_value():
        calls["n"] += 1
        return "" if calls["n"] == 1 else "ok"  # empty result must trigger a retry

    assert providers._retry(empty_then_value) == "ok"
    assert calls["n"] == 2
    err = capsys.readouterr().err
    assert "empty" in err


# ---- claude_complete --------------------------------------------------------

def test_claude_complete_builds_argv_and_returns_stdout(monkeypatch):
    # Subscription mode must run `claude -p` WITHOUT ANTHROPIC_API_KEY/AUTH_TOKEN
    # in the child env, so it uses the claude.ai login, not API billing.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-be-stripped")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok-should-be-stripped")
    # Parent Claude Code session vars must ALSO be stripped so the child `claude -p`
    # runs as a fresh session (leaking them makes it slow + agentic).
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent-session")
    monkeypatch.setenv("CLAUDE_CODE_CHILD_SESSION", "1")
    monkeypatch.setenv("CLAUDE_EFFORT", "high")
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", "{}")
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return SimpleNamespace(stdout="cli-out", returncode=0)

    monkeypatch.setattr(providers.subprocess, "run", fake_run)

    out = providers.claude_complete("claude-haiku-4-5-20251001", "SYS", "PROMPT")

    assert out == "cli-out"
    argv = captured["argv"]
    assert argv[0] == "claude"
    assert "-p" in argv
    assert "PROMPT" in argv
    assert "--model" in argv
    assert argv[argv.index("--model") + 1] == "claude-haiku-4-5-20251001"
    assert "--append-system-prompt" in argv
    assert argv[argv.index("--append-system-prompt") + 1] == "SYS"
    assert "--output-format" not in argv  # text mode: no CLI result envelope
    kwargs = captured["kwargs"]
    assert kwargs["check"] is True
    assert kwargs["timeout"] == config.MODEL_TIMEOUT
    assert "ANTHROPIC_API_KEY" not in kwargs["env"]
    assert "ANTHROPIC_AUTH_TOKEN" not in kwargs["env"]
    assert "CLAUDE_CODE_SESSION_ID" not in kwargs["env"]
    assert "CLAUDE_CODE_CHILD_SESSION" not in kwargs["env"]
    assert "CLAUDE_EFFORT" not in kwargs["env"]
    assert "CLAUDE_PLUGIN_DATA" not in kwargs["env"]


# ---- claude_stream ----------------------------------------------------------

# A realistic multi-line stream-json transcript: a system line, a top-level
# thinking line, an assistant line whose message.content has a thinking block
# AND a text block, then a result line. Only the text block must be yielded.
SAMPLE_STREAM_JSON = "\n".join([
    '{"type":"system","subtype":"init","session_id":"abc"}',
    '{"type":"thinking","thinking":"hmm"}',
    '{"type":"assistant","message":{"content":['
    '{"type":"thinking","thinking":"plotting"},'
    '{"type":"text","text":"HELLO"}]}}',
    '{"type":"result","subtype":"success","result":"HELLO"}',
])


def _fake_popen(lines, returncode):
    class FakeProc:
        def __init__(self):
            self.stdout = iter(lines)
            self.returncode = None  # set by wait(), like real Popen

        def wait(self):
            self.returncode = returncode
            return returncode

        def kill(self):
            pass  # noop; the timer never fires in tests but proc.kill must be callable

    return FakeProc()


def test_claude_stream_yields_only_assistant_text_blocks(monkeypatch):
    lines = SAMPLE_STREAM_JSON.splitlines(keepends=True)
    monkeypatch.setattr(
        providers.subprocess, "Popen",
        lambda *a, **k: _fake_popen(lines, returncode=0),
    )

    out = list(providers.claude_stream("m", "SYS", "PROMPT"))

    assert out == ["HELLO"]  # system/thinking/result skipped; thinking block skipped


def test_claude_stream_raises_when_no_text(monkeypatch):
    lines = [
        '{"type":"system","subtype":"init"}\n',
        '{"type":"result","subtype":"success","result":""}\n',
    ]
    monkeypatch.setattr(
        providers.subprocess, "Popen",
        lambda *a, **k: _fake_popen(lines, returncode=0),
    )

    with pytest.raises(providers.ModelError):
        list(providers.claude_stream("m", "SYS", "PROMPT"))


def test_claude_stream_raises_on_nonzero_returncode(monkeypatch):
    lines = [
        '{"type":"assistant","message":{"content":[{"type":"text","text":"HELLO"}]}}\n',
    ]
    monkeypatch.setattr(
        providers.subprocess, "Popen",
        lambda *a, **k: _fake_popen(lines, returncode=1),
    )

    with pytest.raises(providers.ModelError):
        list(providers.claude_stream("m", "SYS", "PROMPT"))


def test_claude_stream_builds_argv_and_strips_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-be-stripped")
    captured = {}

    def fake_popen(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        lines = [
            '{"type":"assistant","message":{"content":[{"type":"text","text":"STREAMED"}]}}\n',
        ]
        return _fake_popen(lines, returncode=0)

    monkeypatch.setattr(providers.subprocess, "Popen", fake_popen)

    out = list(providers.claude_stream("claude-haiku-4-5-20251001", "SYS", "PROMPT"))

    assert out == ["STREAMED"]
    argv = captured["argv"]
    assert "claude" in argv
    assert "-p" in argv
    assert "PROMPT" in argv
    assert "--model" in argv
    assert argv[argv.index("--model") + 1] == "claude-haiku-4-5-20251001"
    assert "--output-format" in argv
    assert "stream-json" in argv
    assert "--verbose" in argv
    assert "--append-system-prompt" in argv
    assert argv[argv.index("--append-system-prompt") + 1] == "SYS"
    kwargs = captured["kwargs"]
    assert "ANTHROPIC_API_KEY" not in kwargs["env"]


# ----------------------------------------------------------------------------
# OpenRouter provider (OpenAI-compatible via the `openai` SDK)
# ----------------------------------------------------------------------------
def _chunk(text):
    """A fake streaming chunk shaped like an OpenAI delta event."""
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])


def _fake_openai(monkeypatch, captured, *, content="or-out", stream_chunks=None):
    """Install a fake `openai` module on providers + a test API key.

    OpenAI(base_url=, api_key=) -> fake client whose chat.completions.create(**kw)
    records kw in `captured` and returns either a message object (non-stream) or
    the provided `stream_chunks` iterable (stream=True).
    """
    monkeypatch.setattr(config, "openrouter_api_key", lambda: "test-key")

    class FakeCompletions:
        def create(self, **kwargs):
            captured["create_kwargs"] = kwargs
            if kwargs.get("stream"):
                return stream_chunks if stream_chunks is not None else []
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self, *, base_url, api_key):
            captured["base_url"] = base_url
            captured["api_key"] = api_key
            self.chat = FakeChat()

    monkeypatch.setattr(providers, "openai", SimpleNamespace(OpenAI=FakeClient))


def test_openrouter_complete_returns_content_and_wires_client(monkeypatch):
    captured = {}
    _fake_openai(monkeypatch, captured, content="hi there")

    out = providers.openrouter_complete("model-x", "SYS", "PROMPT")

    assert out == "hi there"
    assert captured["base_url"] == config.OPENROUTER_BASE_URL
    assert captured["api_key"] == "test-key"
    kw = captured["create_kwargs"]
    assert kw["model"] == "model-x"
    assert kw["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "PROMPT"},
    ]
    assert "response_format" not in kw  # default: no JSON mode


def test_openrouter_complete_json_out_adds_response_format(monkeypatch):
    captured = {}
    _fake_openai(monkeypatch, captured)

    providers.openrouter_complete("model-x", "SYS", "PROMPT", json_out=True)

    assert captured["create_kwargs"]["response_format"] == {"type": "json_object"}


def test_openrouter_stream_yields_deltas_in_order_skipping_none(monkeypatch):
    captured = {}
    chunks = [_chunk("Hel"), _chunk(None), _chunk("lo"), _chunk("")]
    _fake_openai(monkeypatch, captured, stream_chunks=chunks)

    out = list(providers.openrouter_stream("model-x", "SYS", "PROMPT"))

    assert out == ["Hel", "lo"]  # None and "" deltas dropped, order preserved
    kw = captured["create_kwargs"]
    assert kw["stream"] is True
    assert kw["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "PROMPT"},
    ]


def test_openrouter_stream_raises_modelerror_mid_stream(monkeypatch):
    def _raising_stream():
        yield _chunk("partial")
        raise RuntimeError("mid-stream boom")

    captured = {}
    _fake_openai(monkeypatch, captured, stream_chunks=_raising_stream())

    with pytest.raises(providers.ModelError):
        list(providers.openrouter_stream("model-x", "SYS", "PROMPT"))


def test_openrouter_stream_raises_modelerror_on_empty_output(monkeypatch):
    captured = {}
    _fake_openai(monkeypatch, captured, stream_chunks=[])

    with pytest.raises(providers.ModelError):
        list(providers.openrouter_stream("model-x", "SYS", "PROMPT"))


# ---------------------------------------------------------------------------
# complete() / stream() provider dispatch
# ---------------------------------------------------------------------------
from app.types import RoleConfig  # noqa: E402  (grouped with dispatch tests)


def test_complete_routes_to_claude_subscription(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        providers,
        "claude_complete",
        lambda model, system, prompt: calls.update(model=model, system=system, prompt=prompt)
        or "claude-out",
    )
    monkeypatch.setattr(
        providers,
        "openrouter_complete",
        lambda *a, **k: pytest.fail("openrouter_complete must not be called for claude role"),
    )

    out = providers.complete(RoleConfig("claude-subscription", "m"), "SYS", "PROMPT")

    assert out == "claude-out"
    assert calls == {"model": "m", "system": "SYS", "prompt": "PROMPT"}


def test_complete_routes_to_openrouter_with_json_out(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        providers,
        "openrouter_complete",
        lambda model, system, prompt, *, json_out=False: calls.update(
            model=model, system=system, prompt=prompt, json_out=json_out
        )
        or "or-out",
    )
    monkeypatch.setattr(
        providers,
        "claude_complete",
        lambda *a, **k: pytest.fail("claude_complete must not be called for openrouter role"),
    )

    out = providers.complete(RoleConfig("openrouter", "x/y"), "SYS", "PROMPT", json_out=True)

    assert out == "or-out"
    assert calls == {"model": "x/y", "system": "SYS", "prompt": "PROMPT", "json_out": True}


def test_complete_raises_for_unknown_provider():
    with pytest.raises(ValueError):
        providers.complete(RoleConfig("bogus", "m"), "S", "P")


def test_stream_routes_to_claude_subscription(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        providers,
        "claude_stream",
        lambda model, system, prompt: calls.update(model=model, system=system, prompt=prompt)
        or iter(["a", "b"]),
    )
    monkeypatch.setattr(
        providers,
        "openrouter_stream",
        lambda *a, **k: pytest.fail("openrouter_stream must not be called for claude role"),
    )

    out = list(providers.stream(RoleConfig("claude-subscription", "m"), "SYS", "PROMPT"))

    assert out == ["a", "b"]
    assert calls == {"model": "m", "system": "SYS", "prompt": "PROMPT"}


def test_stream_routes_to_openrouter(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        providers,
        "openrouter_stream",
        lambda model, system, prompt: calls.update(model=model, system=system, prompt=prompt)
        or iter(["x"]),
    )
    monkeypatch.setattr(
        providers,
        "claude_stream",
        lambda *a, **k: pytest.fail("claude_stream must not be called for openrouter role"),
    )

    out = list(providers.stream(RoleConfig("openrouter", "x/y"), "SYS", "PROMPT"))

    assert out == ["x"]
    assert calls == {"model": "x/y", "system": "SYS", "prompt": "PROMPT"}


def test_stream_raises_for_unknown_provider():
    # stream() must raise ValueError eagerly on call, not lazily on first iteration.
    with pytest.raises(ValueError):
        providers.stream(RoleConfig("bogus", "m"), "S", "P")


# ---------------------------------------------------------------------------
# Fix 1: claude_complete and claude_stream pass a cwd OUTSIDE the framework root
# (so `claude -p` does not adopt the project's CLAUDE.md persona).
# ---------------------------------------------------------------------------

def test_claude_complete_passes_clean_cwd(monkeypatch):
    captured = {}

    def fake_run(argv, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        return SimpleNamespace(stdout="ok", returncode=0)

    monkeypatch.setattr(providers.subprocess, "run", fake_run)

    providers.claude_complete("m", "SYS", "PROMPT")

    cwd = captured["cwd"]
    assert cwd is not None
    assert str(config.FRAMEWORK_ROOT) not in cwd
    import os
    assert os.path.isdir(cwd)


def test_claude_stream_passes_clean_cwd(monkeypatch):
    captured = {}

    def fake_popen(argv, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        lines = [
            '{"type":"assistant","message":{"content":[{"type":"text","text":"HI"}]}}\n',
        ]
        return _fake_popen(lines, returncode=0)

    monkeypatch.setattr(providers.subprocess, "Popen", fake_popen)

    list(providers.claude_stream("m", "SYS", "PROMPT"))

    cwd = captured["cwd"]
    assert cwd is not None
    assert str(config.FRAMEWORK_ROOT) not in cwd
    import os
    assert os.path.isdir(cwd)


# ---------------------------------------------------------------------------
# Fix 2: claude_stream creates a threading.Timer with MODEL_TIMEOUT watchdog
# ---------------------------------------------------------------------------

def test_claude_stream_uses_timeout_watchdog(monkeypatch):
    timer_args = {}
    timer_calls = []

    class FakeTimer:
        def __init__(self, interval, fn):
            timer_args["interval"] = interval
            timer_args["fn"] = fn

        def start(self):
            timer_calls.append("start")

        def cancel(self):
            timer_calls.append("cancel")

    monkeypatch.setattr(providers.threading, "Timer", FakeTimer)

    lines = [
        '{"type":"assistant","message":{"content":[{"type":"text","text":"HI"}]}}\n',
    ]
    monkeypatch.setattr(
        providers.subprocess, "Popen",
        lambda *a, **k: _fake_popen(lines, returncode=0),
    )

    list(providers.claude_stream("m", "SYS", "PROMPT"))

    assert timer_args["interval"] == config.MODEL_TIMEOUT
    assert "start" in timer_calls
    assert "cancel" in timer_calls


# ---------------------------------------------------------------------------
# Fix 4: complete() does NOT forward json_out to claude_complete (no-op path)
# ---------------------------------------------------------------------------

def test_complete_claude_subscription_does_not_forward_json_out(monkeypatch):
    calls = []
    # 3-arg lambda: would raise TypeError if json_out were forwarded as a kwarg
    monkeypatch.setattr(
        providers,
        "claude_complete",
        lambda model, system, prompt: calls.append((model, system, prompt)) or "ok",
    )

    out = providers.complete(RoleConfig("claude-subscription", "m"), "SYS", "PROMPT", json_out=True)

    assert out == "ok"
    assert len(calls) == 1  # called exactly once with only positional args
    # The 3-arg lambda succeeding proves json_out was NOT forwarded to claude_complete.
