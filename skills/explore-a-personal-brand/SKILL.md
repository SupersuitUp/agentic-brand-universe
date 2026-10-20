---
name: explore-a-personal-brand
description: Turn a person's sense of how their pages should look into a real brand universe they approved by looking at it. Reads their site if they have one, interviews them by voice on their phone if they do not, writes three genuinely different directions, renders a brand board for each, puts the three side by side on their phone, refines until they say yes, and only then seeds a private brand universe (palette, type, mark, brief) that every page they publish can read. Use when the operator says "make me a brand", "I need my pages to look like me", "explore my brand", "what should my artifacts look like", "brand my hub", or when a hub or page needs a brand and none exists. NOT for a company brand with a team and a history (that is start-new-story-universe plus a human brand process) and NOT for a single image (on-brand-image).
---

# Explore a personal brand

The output is a private ABU universe the operator approved on their phone. Pluma proposes; the
operator decides. **Never decide the brand for them.** Three directions are a question put to
them, not a recommendation dressed as one, and nothing is blessed, locked or called golden before
their yes.

The scripts live in `scripts/` beside this file and need Node 22+ and Chrome:
`read-site.mjs`, `render-board.mjs` (with `contrast.mjs`, `mark.mjs`, `fonts.mjs`,
`glyph-paths.py`, `cdp.mjs`). The engine verbs are `abu init` and `abu seed`.

## 1. Read what the workspace already knows

Read the operator's profile (`self/self.md`, the identity and voice files, any existing brand
or artifact-hub notes) **before saying anything**. Never ask what the workspace already answers:
their name, what they do, who they write for, a site they have named. A question whose answer
is on disk is toil handed back. Carry what you learned into the interview as the starting
point ("the profile says you write for founders, still true?"), not as a blank.

## 2. Ask the one starting question

If the profile does not already settle it, ask with `AskUserQuestion`, exactly three answers,
worded with the operator's name (say-who-acts: never "you", never "I"), the third as the default (marked `(default)`):

- **<Name>'s site is the brand** (the site already looks like them; read it, keep it)
- **<Name> has a site, but it is not really the brand** (read it for what it shows, ignore what it does not)
- **<Name> does not have one yet (default)** (start from the interview)

The off-list answer lives in the question text, because a preview would cost the visible
`Other` row. Do not add a fourth option.

## 3. Read the site, when there is one

```bash
node skills/explore-a-personal-brand/scripts/read-site.mjs <url> --out <work>/site
```

It writes `site-read.json` plus the logo, favicon and phone and desktop screenshots.
`toDirection` in `read-site.mjs` turns a read into a valid direction for the "site is the brand"
case; a font that is not on Google Fonts is swapped for the closest Google family and the
original is recorded in `sources`. Look at the two screenshots yourself.

**Say plainly when a site is thin.** A one-page site with default colors, no logo and system
fonts has no brand to keep. Say that in a sentence ("there is not much here to build on: one
color, no mark") and lean on the interview instead. A read that could not resolve a ground or a
text color says so in `unresolved`; report that rather than guessing. Never pad a thin read into a
confident palette.

## 4. Interview by voice, on their phone

Run it through `freedom:interview-me` (slug `<name>-brand`), so they answer out loud on their
phone and the words land in the workspace. Skip anything the profile or the site read already
answers. The questions, in this order, choosing each next one from the last answer:

1. Who are the pages for?
2. Three words a reader should feel.
3. Looks they admire (a site, a magazine, a room, anything).
4. What they never want to look like.
5. Anything already theirs: a color they wear, a logo, a typeface, a nickname.

**Stop as soon as three distinct directions can be named.** Not at five questions, not at a
quota: the moment you could write three one-line concepts that would not be mistaken for each
other, the interview is over. If they press "I'm ready" earlier, that also ends it.

## 5. Write three directions that differ in concept

Write three `direction.json` files (shape in `scripts/direction.mjs`, mirrored by the engine's
`validate_direction`):

```json
{ "name": "Night Workshop", "concept": "one line",
  "palette": { "ground": "#101418", "ink": "#e9e4da", "accent": "#c8743a",
               "lightGround": "#f6f2ea", "lightInk": "#1a1a1a" },
  "type": { "display": "Fraunces", "body": "Inter" },
  "mark": { "kind": "monogram", "letters": "WF", "treatment": "serif-ligature" },
  "sources": [{ "choice": "accent", "from": "interview", "detail": "q3: burnt orange" }] }
```

**The three differ in concept, not in palette alone.** Three palettes on one idea is one
direction rendered three times. A concept is a stance ("a workshop at night", "a printed
broadsheet", "a quiet clinic"), and each stance should push palette, type and mark in a
different direction. Record where each choice came from in `sources`; every choice should trace
to something they said or something the site showed.

A kept site becomes **one of the three** (the one that is the site, faithfully), and the other
two are real alternatives. Fonts must exist on Google Fonts; a mark is a monogram or an SVG, and a
raster logo is traced to SVG before it counts.

## 6. Render all three boards in parallel

```bash
node skills/explore-a-personal-brand/scripts/render-board.mjs <work>/a.json --out <work>/a.png &
node skills/explore-a-personal-brand/scripts/render-board.mjs <work>/b.json --out <work>/b.png &
node skills/explore-a-personal-brand/scripts/render-board.mjs <work>/c.json --out <work>/c.png &
wait
```

Each run also writes `<name>.fixed.json` (the direction with its contrast-fixed palette and
`contrastNotes`) and `<name>.mark.svg` (the mark as path outlines) beside the input. **The fixed
file is the one that is seeded**, so the canon and the board always agree. Read the board's
footer: it names any contrast adjustment and any font that stood in. Look at every board before
sending it.

## 7. Put the three side by side on their phone

```
ask_operator({ kind: "compare", items: [<a.png>, <b.png>, <c.png>] })
```

Name each card with its concept, not a letter. Two taps to pick, and the "Other" box is always on
screen: a mix is a legitimate answer. Link the page in the chat reply (named, never bare).

## 8. Refine until they say yes

A pick with a note ("this one, but warmer, and not that mark") or a mix ("A's type, C's
palette") is a refine round, not a yes. Change the chosen direction, re-render its board (and the
runner-up if it is still live), and compare again. Repeat until they **say yes in their own
words**. A tap on the best of three is a pick; "yes, this is it" is the yes.

**Nothing is golden before that yes.** Do not seed, do not lock a mark, do not file a brief as
approved on a pick alone, and do not describe a candidate as the brand.

## 9. On yes: make the universe

```bash
abu init <repos>/<slug>-universe --name <slug>-brand
abu seed <repos>/<slug>-universe --from <work>/<chosen>.fixed.json \
    --brief <work>/brand-brief.md --mark <work>/<chosen>.mark.svg --board <work>/<chosen>.png
```

- Write `brand-brief.md` first, in the operator's own words from the interview: who the pages
  are for, the three words, what they admire, what they refuse, what was already theirs, and the
  concept in one line. It is what a future session reads before touching the brand.
- `abu seed` writes the palette, type and mark into canon, declares `identity.surfaces` so a
  page reads the colors by role, and makes the board the register anchor. Every file it writes
  carries a recipe.
- Then make it a private repo and push:
  `gh repo create <owner>/<slug>-universe --private --source <universe> --push`.
  `<owner>` is the operator's own GitHub account or organization, read from their workspace.
- **Return the universe path** (and the repo link) as the result, and say where the board and the
  brief are.

If the operator already has a universe dir convention (look where their other universes live),
use it instead of the default `<repos>` location.

## Refusals

- Never choose for them, and never mark a direction "(Recommended)".
- Never ask what the profile already answers.
- Never ship three palettes on one concept.
- Never call anything golden, or lock a mark, before their yes.
- Never invent: no made-up quotes, no claimed influences they did not name.
- A thin brand is said plainly, never padded.

<!-- BEGIN GENERATED: report -->
## When this skill misfires, offer to report it

If this skill did not one-shot (a step failed, a check refused something it should not have, an instruction sent you the wrong way, you fixed its output by hand, or it left out an obvious step), the person running it is the only one who knows, and only right now. Offer once, in one line, to report it. On a yes, run it yourself and never show them the command:

    abu report "<what happened>" --expected "<what should have happened, and why>" --command "<the exact command or ask>" --skill abu:explore-a-personal-brand

Write every field from what you just watched: an issue that says what was expected and how to reproduce it gets fixed, and "it broke" does not. A `check-kit` refusal they believe is wrong is `abu check-kit ... --report`, which attaches the findings and the rule each one broke. It prints a pre-filled GitHub issue and sends nothing: hand them the link to read and submit. Inside Freedom, `freedom:suggest-an-improvement` files it for them. If you maintain ABU itself, fix it through `evolve-abu` instead.
<!-- END GENERATED: report -->
