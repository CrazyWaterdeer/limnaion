# Limnaion 🐸

A terminal text-TRPG hosted by **Brekekos Limnaios** — the frog-chorus GM of
Aristophanes' *Frogs*, who ferries you across the marsh into your story and back out.

- Narration in **Korean**; the GM screen (rules, stats, dice) stays in English and **hidden by default**.
- Real **2d6** dice resolve every uncertain action — the model never fakes a roll.
- Two model backends, switchable per role in Settings: your **Claude subscription**
  (via the `claude` CLI) or **OpenRouter** (Gemini, GPT, Claude, DeepSeek, … — live model list).

## Install

```bash
pipx install git+https://github.com/CrazyWaterdeer/limnaion.git
# or, from a clone:
pip install .
```

(For development this repo is run via `uv`: `uv run --project /path/to/your/uv-env python -m app.main tui`.)

## Prerequisites

- **Claude subscription path:** the [`claude` CLI](https://docs.anthropic.com/claude-code) installed and logged in (run `claude` and `/login`). The narrator defaults to Opus; referee/scribe use Haiku.
- **OpenRouter path:** set your key in **Settings (F3 → OpenRouter API 키)**, or the `OPENROUTER_API_KEY` environment variable.

## Run

```bash
limnaion           # the splash hub: new game / load / settings
limnaion <slug>    # jump straight into a saved game
```

Games are stored per-user (`platformdirs` data dir); set `LIMNAION_GAMES_DIR` to override.

## Keys

`Tab` 상태 패널 · `F1` 도움말 · `F2` 상태/캐릭터/등장인물 · `F3` 설정 · `^E` 에필로그 · `^B` 메인으로 · `^Q` 종료.
Input: `*행동*` (행동), `"대사"` (말), `(ooc) 메모`.

## Play in a browser / on your phone

From a git clone:

```bash
python serve.py                       # then open http://localhost:8000
textual-web --config textual-web.toml # a public URL for your phone (after `textual-web --signup`)
```

The app (and your Claude subscription) run on your machine; only the screen is served. Keep it personal.

## License

GPL-3.0 — see `LICENSE`.
