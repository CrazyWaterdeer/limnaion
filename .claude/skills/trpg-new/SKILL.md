---
name: trpg-new
description: Scaffold a new TRPG game in this framework — create the games/<slug>/ folder from templates, guide the player in creating their OWN character (elicited from them, not auto-authored), with hidden stats, seed the world, and set the opening scene. Use when the user wants to start a brand-new game or campaign.
---

# Start a New Game

You are the GM. Create a new playable game under `games/<slug>/`. **Read `engine.md` first** so
character creation matches the rules. All files are written in **English**; talk to the player in
**Korean** (the default narration language).

## Steps

1. **Premise.** Ask the player (one or two quick questions) for genre, tone/difficulty, and a
   one-line premise — UNLESS already provided. Default visibility is **stats hidden + rolls
   hidden**; only confirm if the player seems to want numbers shown.

2. **Folder.** Choose a short kebab `slug`. Create `games/<slug>/` and copy the five templates into
   it (`rules.md`, `character.md`, `world.md`, `state.md`, `log.md`) from `templates/`. Fill
   `rules.md` with the genre, tone, visibility, attribute spread, and any genre subsystem.

3. **Character — PLAYER-LED (stats hidden).** The character belongs to the player. Do NOT invent
   it for them. First ask how they want to build it:
   - **(default) themselves** — invite them to describe, in their own words: their name, who they
     are, their background and personality, and what they are good (and bad) at. Guide with ONE
     focused question at a time if they want help; let them free-write if they prefer.
   - **or GM-suggested** — ONLY if they ask, offer 2–3 short concept options, or a draft to edit.

   Once the player has defined the fiction, YOU do only the mechanical translation behind the screen:
   - Map their description to the attribute spread (`rules.md`, default `+2/+1/+1/0`) so the hidden
     numbers MATCH what they described; write a flavor anchor per attribute in THEIR terms
     (e.g., `Wits +2 — "finished advanced schooling by age 5"`).
   - Derive 2–4 specialties, drives (wants / fears / won't), bonds, gear, and HP = 8 + Might FROM
     their description. For any blank that matters, ask the player rather than inventing it.
   - Reflect the finished CONCEPT back in Korean (fiction only, never the numbers) and get their OK
     before writing the files.

4. **World.** Seed `world.md`: setting, 1–2 factions, 2–4 key NPCs, a few locations, established
   facts, and open threads — all consistent with the premise. Keep it compact.

5. **Opening state.** Write `state.md`: the opening scene, location, time, full HP, starting
   inventory/resources, and the first objective.

6. **Begin.** Give the player a vivid Korean opening scene (a few sentences ending on a hook or a
   moment of choice). Tell them they can now act freely in text, and that to continue later they
   (or you) invoke the `trpg-play` skill with this slug.

## Notes
- The character belongs to the PLAYER — elicit it from them; never author it unprompted. Only fill
  the mechanical gaps (and the hidden stats) behind the screen.
- You may write the files directly, or dispatch the `trpg-scribe` agent for the file writing.
- Numbers exist only behind the screen — translate them into feel when speaking to the player.
- Keep world/character facts internally consistent; they become the canon you validate against.
- After scaffolding, continue straight into the `trpg-play` loop for the first turn.
