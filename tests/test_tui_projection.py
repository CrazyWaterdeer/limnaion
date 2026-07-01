from app.tui import projection
from app.types import GameFiles

STATE = """# Current State: The Eastern Passage

- **Scene:** Kael wades thigh-deep through a narrowing corridor.
- **Location:** The Eastern Passage
- **Time:** Night, deep underground
- **Condition:** HP 10/10
- **Resources:** —
- **Inventory:** notched longsword, guttering oil lantern
- **Active Objectives:**
  - [ ] Navigate the flooded chamber and locate the bounty
  - [x] Investigate the eastward-marked passage
- **Status Effects:** none
- **Last turn #:** 4"""

CHARACTER = """# Character: Kael

## Concept
A scarred mercenary — strong and stubborn, quick with a blade.

## Attributes  (hidden)
- **Might** +2 — "carries a wounded comrade for miles"
- **Agility** +1
- **Presence** 0

## Specialties
- Swordplay
- Survival

## Drives & Personality
- **Wants:** the bounty behind the iron door
- **Fears:** being buried alive

## Bonds & Relationships
- Mara — the broker who hired him

## Background
A sellsword who has cleared a dozen ruins.

## Assets / Signature Gear
- A notched longsword

## Notes
HP max = 8 + Might. Live condition is tracked in state.md.
"""

WORLD = "# World: The Iron Door\n\nA flooded ruin."


def _game(state=STATE, character=CHARACTER, world=WORLD, slug="demo") -> GameFiles:
    return GameFiles(slug=slug, engine="", rules="", character=character,
                     world=world, state=state, log="")


def test_game_title_strips_world_prefix():
    assert projection.game_title(_game()) == "The Iron Door"


def test_game_title_falls_back_to_slug():
    assert projection.game_title(_game(world="no heading here", slug="myslug")) == "myslug"


def test_turn_number_reads_state():
    assert projection.turn_number(_game()) == 4
    assert projection.turn_number(_game(state="no turn line")) == 0


def test_parse_state_fields():
    f = projection.parse_state_fields(STATE)
    assert f["Scene"].startswith("Kael wades")
    assert f["Location"] == "The Eastern Passage"
    assert f["Condition"] == "HP 10/10"


def test_parse_objectives():
    objs = projection.parse_objectives(STATE)
    assert (False, "Navigate the flooded chamber and locate the bounty") in objs
    assert (True, "Investigate the eastward-marked passage") in objs


def test_wound_band_words_hp_and_hides_numbers():
    assert projection.wound_band("HP 10/10") == "멀쩡함"
    assert projection.wound_band("HP 6/10") == "긁힌 상처"
    assert projection.wound_band("HP 4/10") == "부상"
    assert projection.wound_band("HP 1/10") == "중상"
    assert projection.wound_band("HP 0/10") == "빈사 상태"
    # HP-regex branch: result is a word, no digits
    assert "10" not in projection.wound_band("HP 10/10")


def test_wound_band_fallback_strips_standalone_digits():
    # A2: fallback branch must not leak any digit to the player
    assert "2" not in projection.wound_band("Poisoned (2 rounds)")
    assert "10" not in projection.wound_band("HP 10 remaining")
    # worded conditions pass through unchanged
    assert projection.wound_band("Bruised") == "Bruised"
    # empty string yields the default word
    assert projection.wound_band("") == "멀쩡함"
    # Korean worded condition passes through unharmed
    assert projection.wound_band("부상") == "부상"


def test_status_lines_hide_numbers():
    lines = projection.status_lines(_game())
    blob = "\n".join(lines)
    assert "멀쩡함" in blob          # condition worded
    assert "10/10" not in blob       # raw HP never shown
    assert "Navigate the flooded chamber" in blob  # objective surfaced
    assert "Last turn #" not in blob  # turn goes in the header, not the panel


def test_completed_objective_text_visible_in_status_lines():
    # A1: [x] items previously vanished under markup=True — verify they appear.
    state = (
        "# Current State\n"
        "- **Scene:** A flooded corridor.\n"
        "- **Condition:** HP 8/8\n"
        "- **Active Objectives:**\n"
        "  - [x] Investigate the eastward-marked passage\n"
    )
    lines = projection.status_lines(_game(state=state))
    blob = "\n".join(lines)
    assert "Investigate the eastward-marked passage" in blob


def test_character_lines_show_flavor_hide_stats():
    lines = projection.character_lines(_game())
    blob = "\n".join(lines)
    assert "Swordplay" in blob        # specialty shown
    assert "Mara" in blob             # bond shown
    assert "Might" not in blob        # attribute name hidden
    assert "+2" not in blob           # modifier hidden
    assert "HP max" not in blob       # formula hidden


# C1b — game_title handles bare Korean H1 and legacy 'World:' prefix

def test_game_title_bare_korean_h1():
    """C1b: a bare '# <Korean title>' (new creation format) returns the title as-is."""
    game = _game(world="# 철문 너머의 빚\n\n## Setting\nA ruined fen.")
    assert projection.game_title(game) == "철문 너머의 빚"


def test_game_title_legacy_world_prefix_still_stripped():
    """C1b: legacy '# World: <title>' format still returns '<title>' with prefix stripped."""
    assert projection.game_title(_game()) == "The Iron Door"


# C2a — npc_lines extracts only the Key NPCs section

_WORLD_WITH_NPCS = """\
# 철문 너머의 빚

## Setting
A flooded ruin.

## Key NPCs
- **Mara** — the broker who hired the protagonist

## Lore & Established Facts
- Secret: the vault holds something terrible.

## Open Threads
- Where did the debt come from?
"""


def test_npc_lines_returns_key_npcs_entries():
    """C2a: npc_lines includes NPC entries and excludes GM-only sections."""
    game = _game(world=_WORLD_WITH_NPCS)
    lines = projection.npc_lines(game)
    blob = "\n".join(lines)
    assert "Mara" in blob
    # GM-only sections must not leak
    assert "terrible" not in blob
    assert "debt" not in blob


def test_npc_lines_empty_when_no_npcs():
    """C2a: npc_lines returns [] when the Key NPCs section has no entries."""
    world = "# 제목\n\n## Setting\nA place.\n\n## Key NPCs\n\n## Lore\n- secret\n"
    game = _game(world=world)
    assert projection.npc_lines(game) == []
