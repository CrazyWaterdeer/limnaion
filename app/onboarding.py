"""Character creation for the Brekekos onboarding flow.

The player authors the fiction (name, concept, background, strengths, weaknesses, and an
opening-scene seed). This module hands that fiction to the model with ONE instruction: assign
the HIDDEN stats to MATCH the fiction, then write the GM-screen files and open the story. The
result scaffolds a fresh game and seeds character.md / world.md / state.md.

English only in the files (the GM screen); the opening scene is Korean narrator prose.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app import config, game_files, providers
from app.types import RoleConfig


@dataclass
class OnboardingInputs:
    """The fiction the player wrote, collected one onboarding beat at a time."""

    name: str
    concept: str
    background: str
    strengths: str
    weaknesses: str
    scene: str


CREATOR_SYSTEM = """You are the CHARACTER CREATOR for a hidden-stat text TRPG. The player has ALREADY
written the fiction — their character's name, concept, background, strengths, weaknesses, and the
seed of an opening scene. You do NOT rewrite or overrule their fiction. Your job is to translate it
into the GM's mechanical truth and open the story.

Assign the HIDDEN stats to MATCH the fiction, never to overpower it:
- Might, Agility, Wits, Presence — each a SMALL integer modifier in the range -1..+3. A stated
  strength earns a higher modifier in the matching attribute; a stated weakness earns 0 or -1.
  Keep the spread grounded; do not hand out +3 across the board.
- Choose exactly TWO Specialties drawn from what the fiction makes them good at.
- HP max = 8 + Might; the opening Condition is full HP.

Produce FIVE artifacts and return them as ONE JSON object with EXACTLY these keys:
- "title": a short, evocative KOREAN title for this story — like a novel or campaign title (roughly
  2–6 words), drawn from the player's fiction and the seeded scene. Not a generic label.
- "character_md": the FULL character.md. Keep the template's headings verbatim (Concept, Attributes
  (hidden), Specialties, Drives & Personality, Bonds & Relationships, Background, Assets / Signature
  Gear, Notes). Fill each from the player's fiction with the hidden modifiers and flavor anchors.
- "world_md": the FULL world.md body — do NOT include a top-level `# ` title line (the title is
  added separately); start at `## Setting` and keep the template's section headings (Setting,
  Factions, Key NPCs, Locations, Lore & Established Facts, Open Threads). The `## Key NPCs` section
  must list the NPCs implied by the seed. Establish only what the seed implies; leave room for the
  story to discover the rest.
- "state_md": the FULL opening state.md. Keep the template's headings. Put the full Condition/HP
  behind the screen (e.g. "HP 8/8"), an Inventory derived from the character's Assets / Signature
  Gear, and 2-4 concrete Active Objectives. Set Last turn # to 0.
- "opening_scene": vivid SECOND-PERSON KOREAN prose that drops the player into the seeded scene —
  pure narrator voice. No menu, no options, no "무엇을 하시겠습니까?", no mechanics, no numbers.
  This is the ONLY Korean field (along with "title"); character_md / world_md / state_md stay
  English (the GM screen).

Output the JSON object only — no prose around it, no commentary."""

_REQUIRED_KEYS = ("title", "character_md", "world_md", "state_md", "opening_scene")


def _strip_fence(raw: str) -> str:
    """Remove a leading ```json (or bare ```) fence and its trailing ``` if present.

    If the opening fence has no newline following it (bare fence header with no
    body), return an empty string so that ``json.loads`` raises a clear error
    rather than silently receiving the fence header as the body.
    """
    s = raw.strip()
    if s.startswith("```"):
        newline = s.find("\n")
        if newline == -1:
            # No newline after the fence header: treat the body as empty.
            return ""
        s = s[newline + 1 :]
        s = s.rstrip()
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()


def _build_prompt(inputs: OnboardingInputs) -> str:
    char_tpl = game_files.read_text(config.TEMPLATES_DIR / "character.md")
    world_tpl = game_files.read_text(config.TEMPLATES_DIR / "world.md")
    state_tpl = game_files.read_text(config.TEMPLATES_DIR / "state.md")
    return (
        "## The player's fiction (they wrote this; honor it)\n"
        f"Name: {inputs.name}\n"
        f"Concept: {inputs.concept}\n"
        f"Background: {inputs.background}\n"
        f"Strengths: {inputs.strengths}\n"
        f"Weaknesses: {inputs.weaknesses}\n"
        f"Opening scene seed: {inputs.scene}\n\n"
        "## character.md template (keep these headings)\n" + char_tpl + "\n\n"
        "## world.md template (keep these headings)\n" + world_tpl + "\n\n"
        "## state.md template (keep these headings)\n" + state_tpl + "\n"
    )


def create_game(
    slug: str,
    inputs: OnboardingInputs,
    *,
    role: RoleConfig = config.SCRIBE,
    complete=providers.complete,
) -> str:
    """Author a new game from the player's fiction and return its Korean opening scene.

    Makes one JSON model call, validates the four required keys BEFORE touching disk, scaffolds
    the game from templates, then overwrites character.md / world.md / state.md atomically.
    Raises ValueError if the model omits any required key.
    """
    prompt = _build_prompt(inputs)
    raw = complete(role, CREATOR_SYSTEM, prompt, json_out=True)
    data = json.loads(_strip_fence(raw))
    missing = [k for k in _REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"create_game output missing keys: {missing}")

    game_files.new_game_from_templates(slug)
    d = config.game_dir(slug)
    game_files.write_text_atomic(d / "character.md", data["character_md"])
    game_files.write_text_atomic(d / "world.md", f"# {data['title']}\n\n{data['world_md']}")
    game_files.write_text_atomic(d / "state.md", data["state_md"])
    return data["opening_scene"]
