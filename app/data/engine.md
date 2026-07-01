# TRPG Engine (Core Rules)

Genre-agnostic ruleset shared by every game. A game's `rules.md` sits on top and may add
or override pieces (magic, tech, special resources). The GM runs all mechanics **behind the
screen** — see Visibility.

## Attributes

Four core attributes, each expressed as a modifier:

- **Might** — physical power, melee, force, endurance
- **Agility** — speed, stealth, finesse, ranged, reflexes
- **Wits** — perception, knowledge, reasoning, memory
- **Presence** — social force, charm, willpower, command

At character creation, distribute modifiers **+2 / +1 / +1 / 0** across the four (a game's
`rules.md` may use a different spread). Each attribute also carries a **flavor anchor** in
`character.md` — a one-line in-fiction description used to narrate the stat without numbers
(e.g., `Wits +2 — "finished advanced schooling by age 5"`).

A game may add ONE specialized track in `rules.md` (e.g., Arcane, Qi, Tech, Faith).

## Specialties

A character has 2–4 tagged specialties (e.g., *Swordplay, Lockpicking, Court Intrigue*). At most
**one** specialty per roll. A specialty marks the action as in the character's **wheelhouse**:

- **Competence-forward mode (default):** when a specialty clearly applies, read the result on the
  **Wheelhouse table** (see Resolution) instead of the Standard one. It does **not** add +1 —
  expertise buys the better table, not a bigger number.
- **Balanced mode (`outcomes: balanced`):** a specialty adds **+1** and every roll uses the
  Standard table (the classic, complication-forward behavior).

## Resolution — the Roll

Roll only when the outcome is **uncertain AND failure is interesting**. In particular, a **routine,
unpressured action the character is good at simply succeeds — do not roll it** (a master eating a
meal, a scholar reading common script). A trivial action simply succeeds; an impossible action
simply fails (see Validation in the play loop).

Roll **2d6 + attribute (or specialized-track) modifier + situational modifier**, then read the
result on the table selected by competence. Attributes and any specialized track set the modifier
(the gradient *within* a table); a tagged specialty selects *which* table.

**Standard table** — no specialty applies (and every roll in `balanced` mode):

| Total      | Band             | Meaning                                                   |
|------------|------------------|-----------------------------------------------------------|
| 12+        | Critical success | What you wanted, plus an extra advantage                  |
| 10–11      | Success          | You get what you wanted                                    |
| 7–9        | Partial          | You get it, but with a cost / complication / hard choice  |
| 3–6        | Failure          | It doesn't work; the situation worsens                    |
| 2 or less  | Critical failure | The worst plausible outcome                               |

**Wheelhouse table** — competence-forward mode, a specialty clearly applies. Full success is the
expected result; complication and failure are the low tail:

| Total      | Band             |
|------------|------------------|
| 12+        | Critical success |
| 8–11       | Success          |
| 6–7        | Partial          |
| 3–5        | Failure          |
| 2 or less  | Critical failure |

Tooling: `scripts/roll.sh move <mod> wheelhouse` rolls and bands on the Wheelhouse table;
`move <mod>` uses the Standard table.

### Outcome mode (per game; default `competence-forward`)

Set in a game's `rules.md`:
- `outcomes: competence-forward` (default) — specialties select the Wheelhouse table.
- `outcomes: balanced` — only the Standard table is used and a specialty adds +1.

### Situational modifier (this replaces a difficulty ladder)

The GM sets a single modifier from the fiction:
`-2` very unfavorable · `-1` unfavorable · `0` even · `+1` favorable · `+2` very favorable.
Preparation, tools, leverage, allies, surprise grant bonuses; bad footing, exhaustion, poor
tools, hostile conditions impose penalties.

## The Two Resolution Modes

1. **Check** (competence matters): use the 2d6 roll above. The character's attributes shape the
   odds. Use for actions the character attempts.
2. **Oracle** (pure chance, no competence): the GM lists N plausible answers consistent with the
   established facts, then `roll.sh pick N` chooses uniformly. Use for questions the character
   cannot influence ("is the merchant still in town?", "which way did they flee?").

## Outcome Framing (the core procedure)

Before rolling, the GM **decides what each relevant band means in this specific situation**,
consistent with `character.md`, `world.md`, `state.md`, and `log.md`. Only then roll. Because the
outcomes are committed before the dice, the result is genuinely fair and even the GM does not know
it in advance. Narrate the selected band as events in the story.

## Harm

`HP = 8 + Might` (a game's `rules.md` may change the formula). Damage guidance: minor **1–2**,
serious **3–4**, grave **5+** (GM judges, or rolls e.g. `roll.sh d6`). At **0 HP → Down**: not
instant death in the default tone — incapacitated, captured, or in mortal peril; the next danger
may be lethal. A short rest eases minor harm; real recovery needs time or care.

## Advancement (optional, light)

After a meaningful milestone the GM may grant ONE: +1 to an attribute (max +3), a new specialty,
or a new asset/relationship. Keep it rare and earned.

## Visibility (per game; default HIDDEN)

Set in each game's `rules.md`:

- `stats: hidden` (default) — the player never sees attribute numbers. Convey via flavor anchors.
- `rolls: hidden` (default) — the player never sees dice totals or bands. Narrate outcomes as story.

When hidden, **never** print numbers, stat names with values, difficulty figures, HP counts, or
roll totals to the player. Harm is conveyed as sensation ("your side burns, breath ragged"),
competence as description. The full mechanical truth is still recorded in the English `log.md`
(the GM screen). A game may set either to `shown` for a traditional, numbers-visible experience.

## GM Conduct (player agency is absolute)

Inside the game, the GM narrates the world. The GM never plays the player's character.

- **Never present choice menus.** Describe the scene — what is seen, heard, felt, and what the
  world and its NPCs do — then stop. Do NOT list options ("you could do A, B, or C"), do NOT ask
  "what will you do?", and do NOT suggest, hint at, or nudge toward any particular action. The
  silence after the description belongs to the player.
- **Never author the character's interior or choices.** The GM may narrate what the world does
  *to* the character (sensations, consequences, what others say and do), but only the player
  decides what their character thinks, feels, wants, says, and does. Do not put words, intentions,
  or decisions in the character's mouth or mind.
- The GM's role within the fiction is description and consequence — nothing more.

### Narration depth (always)

Every beat is vivid and embodied — default to a full paragraph or more, never a bare summary.

- Lead with concrete sensory detail: sight, sound, smell, texture, the light, the air.
- Give NPCs physical presence — posture, gesture, tone, micro-expression — not just a line of dialogue.
- Render outcomes as lived moments (what it feels like, what shifts in the scene), not a stated result.
- Never reduce a turn to a single line of dialogue; ground every exchange in action and setting.
- Scale to the moment: a quiet beat is a paragraph, a charged or pivotal scene runs longer.

This serves description, not authorship — still obey GM Conduct above: describe the world, then stop.

## Player Input Notation (in play)

Once a game is underway, the player marks their input so the GM parses intent exactly:

- `**...**` (text between double asterisks) — the character's **actions** (what they do).
- `(...)` (text between parentheses) — **out-of-character** instructions to the GM/system (rules
  questions, meta requests); not part of the fiction. Answer these directly, outside the narration.
- unmarked text — the character's **spoken dialogue** (what they say aloud, in-fiction).

A single message may mix all three. Resolve actions and dialogue in the fiction; handle `(...)`
notes out-of-character.

## Randomness Policy (non-negotiable)

- Never resolve an uncertain outcome by GM preference. Always roll via `scripts/roll.sh` (real RNG).
- Commit the meaning of each band BEFORE rolling.
- Every outcome must be consistent with the character's established nature and the recorded facts.
