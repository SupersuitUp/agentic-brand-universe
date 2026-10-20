---
name: explore-a-personal-brand
description: Turn a person's sense of how their pages should look into a real brand universe they approved by looking at it. Reads their site if they have one, interviews them by voice on their phone if they do not, writes three genuinely different directions, renders a brand board for each, puts the three side by side on their phone, refines until they say yes, and only then seeds a private brand universe (palette, type, mark, brief) that every page they publish can read. Use when the operator says "make me a brand", "I need my pages to look like me", "explore my brand", "what should my artifacts look like", "brand my hub", or when a hub or page needs a brand and none exists. NOT for a company brand with a team and a history (that is start-new-story-universe plus a human brand process) and NOT for a single image (on-brand-image).
---

# Explore a personal brand

The output is a private ABU universe the operator approved on their phone. Pluma proposes; the
operator decides. **Never decide the brand for them.** Three directions are a question put to
them, not a recommendation dressed as one, and nothing is blessed, locked or called golden before
their yes.

## Setup: where things are

**Shell state does not persist between tool calls**, so definitions made in one block are gone in the next.
Write the definitions once to `<work>/setup.sh` and **begin every later bash block with `. <work>/setup.sh || exit 1`**
(the blocks below do). Locate ABU the way the other ABU skills do (`make-a-book`'s pattern): `${CLAUDE_PLUGIN_ROOT}` when the harness sets it, else the newest cached
version under any marketplace name, never a hardcoded home path:

```bash
mkdir -p <work> && cat > <work>/setup.sh <<'SETUP'
ABU=${CLAUDE_PLUGIN_ROOT:-$(ls -d ~/.claude/plugins/cache/*/abu/*/ 2>/dev/null | sort -V | tail -1)}
[ -f "$ABU/bin/abu.mjs" ] || { echo "ABU is not installed: run abu:onboard first"; return 1 2>/dev/null || exit 1; }
SK="$ABU/skills/explore-a-personal-brand/scripts"     # read-site.mjs, render-board.mjs, ...
abu() { node "$ABU/bin/abu.mjs" "$@"; }               # the engine, from any directory; needs python3
SETUP
. <work>/setup.sh || exit 1
```

**If ABU is not found, say ABU is not installed and point at `abu:onboard`; do nothing else.**

- **`<work>`** is a scratch folder for this run: `<workspace>/superprojects/<slug>/brand-work/` when the
  operator has a superproject for it, otherwise `mktemp -d`. Boards, directions and the brief live here until the yes.
- **`<slug>`** is the operator's name as a slug (`ada-lovelace`). **`<repos>`** is the folder that holds their
  other repos and universes (the parent of their workspace; look where an existing universe lives and use
  that). **`<owner>`** is their GitHub account: `gh api user -q .login`, unless the workspace names an organization.
- The scripts need Node 22+ and Chrome; the mark and the board need network for Google Fonts.
  **Offline: say so and stop**, since the mark outlines and board fonts cannot be fetched.

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

**If the profile has no URL, ask for it** (one question) before reading anything. The second answer reads the site for
context only: keep **at most the name and one color the operator confirms**, never a whole direction, and do
not make it one of the three. Only the first answer makes the site a direction.

The off-list answer lives in the question text, because a preview would cost the visible
`Other` row. Do not add a fourth option.

## 3. Read the site, when there is one

```bash
. <work>/setup.sh || exit 1
node "$SK/read-site.mjs" <url> --out <work>/site --direction <work>/a.json
```

`--out` gets `site-read.json`, the logo, favicon and phone/desktop screenshots. **`--direction` is the
"site is the brand" route:** it writes `toDirection`'s output (a valid direction taken from the read; a
font not on Google Fonts is swapped for the closest Google family and the original recorded in `sources`).
That file is **direction 1 of the 3** (`a.json`), kept faithful to the site; directions 2 and 3 are real
alternatives written in step 5. For the "not really the brand" answer, omit `--direction`. Look at the
two screenshots yourself.

Failures, each with its action:
- **HTTP error, a redirect to a login page, or an unreachable host:** `read-site` exits 1 and says which.
  Treat it as no site: tell the operator in one line and go to the interview. Never read an error page as a brand.
- **A thin read** (default colors, no logo, system fonts, `unresolved` set): **say so plainly**
  ("there is not much here to build on: one color, no mark") and lean on the interview. Never pad it into a confident palette.
- **A raster logo only** (no SVG): the mark is drawn as a monogram instead, and the raster is shown beside the board
  as a reference only. If the operator insists on tracing it, the vector-logo rule's tool is potrace via
  `uv run --with potracer --with pillow --with numpy` (see `freedom:create-image` craft.md; trace the background
  mask, ship the SVG, proof it at 16 to 36px), and it only counts as the mark once they approve the trace.

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
               "lightGround": "#f6f2ea", "lightInk": "#1a1a1a", "lightAccent": "#a5552a" },
  "type": { "display": "Fraunces", "body": "Inter" },
  "mark": { "kind": "monogram", "letters": "WF", "treatment": "serif-ligature" },
  "sources": [{ "choice": "accent", "from": "interview", "detail": "q3: burnt orange" }] }
```

**The three differ in concept, not in palette alone.** Three palettes on one idea is one
direction rendered three times. A concept is a stance ("a workshop at night", "a printed
broadsheet", "a quiet clinic"), and each stance should push palette, type and mark in a
different direction. Record where each choice came from in `sources`; every choice should trace
to something they said or something the site showed.

A kept site becomes **one of the three** (`a.json` from step 3, faithfully), and the other
two are real alternatives. Fonts should exist on Google Fonts (a stand-in is used and named if not); a mark is a monogram or an
SVG, never a raster.

## 6. Render all three boards in parallel

```bash
. <work>/setup.sh || exit 1
node "$SK/render-board.mjs" <work>/a.json --out <work>/a.png > <work>/a.log 2>&1 & pa=$!
node "$SK/render-board.mjs" <work>/b.json --out <work>/b.png > <work>/b.log 2>&1 & pb=$!
node "$SK/render-board.mjs" <work>/c.json --out <work>/c.png > <work>/c.log 2>&1 & pc=$!
wait $pa || echo "board a failed"; wait $pb || echo "board b failed"; wait $pc || echo "board c failed"
```

Collect each exit code. **A failed board is re-rendered once on its own, then reported** (with its log) rather
than silently dropped. Afterwards check that every `<x>.png`, `<x>.fixed.json` and `<x>.mark.svg` exists.

Each run writes `<name>.fixed.json` (the direction with its contrast-fixed palette and `contrastNotes`) and
`<name>.mark.svg` (the mark as path outlines) beside the input. **The fixed file is the one that is seeded**,
so the canon and the board always agree. Read the board's footer: it names any contrast adjustment, any font
that stood in, and any font it could not check. Look at every board before sending it.

## 7. Put the three side by side on their phone

```
ask_operator({
  kind: "compare",
  title: "Which direction feels like <Name>?",
  source: "<slug>-brand-r<n>",          // lowercase slug, at most 48 chars; <n> is the round, so a re-round is a new ask
  why: "Picks the brand for <Name>'s pages; nothing is seeded until they say yes",
  items: [
    { id: "a", label: "<concept A, in a few words>", image: "<abs work>/a.png" },
    { id: "b", label: "<concept B, in a few words>", image: "<abs work>/b.png" },
    { id: "c", label: "<concept C, in a few words>", image: "<abs work>/c.png" }
  ]
})
```

`image` is the **absolute path** of the board PNG; label each card with its concept, not a letter. Two taps to
pick, and the "Other" box is always on screen (`allowOther` defaults to true): a mix is a legitimate answer.
A review reaches them as a Helm notification (not a texted link); the result carries a `chatLink`, so also
link the page in the chat reply, named, never bare.

What each result status means:
- **status "fallback"** (the phone is not reachable): show the three PNGs with `AskUserQuestion` previews (the
  options are the artifact here, so a preview is right), put the off-list answer in the question text, and say
  once which row was red. Reason `probe-unknown` is a status check that could not run: run `tile_app_status`
  and, if its rows are green, call `ask_operator` again before falling back.
- **status "handoff"**: the page is live; keep waiting with `run-a-review`'s watch (`watch-card.sh <source>` for a decision
  card). With reason `send-failed` the text to their phone failed: put the page's `chatLink` in the chat, say so, then watch.
- **status "timeout"**: they did not answer in time. Say so and ask again later; **never proceed on silence**, and never seed.

## 8. Refine until they say yes

A pick with a note ("this one, but warmer, and not that mark") or a mix ("A's type, C's
palette") is a refine round, not a yes. Turn a note or a mix into a new `direction.json`: copy the chosen one, edit the palette, type or mark,
and append a `sources` entry `{choice, from: "refine", detail: <their words>}`. Re-render its board (at most
three live boards per round) and compare again. Repeat until they **say yes in their own
words**. A tap on the best of three is a pick; "yes, this is it" is the yes.

**Nothing is golden before that yes.** Do not seed, do not lock a mark, do not file a brief as
approved on a pick alone, and do not describe a candidate as the brand.

## 9. On yes: make the universe

```bash
. <work>/setup.sh || exit 1
U=<repos>/<slug>-universe
abu init "$U" --name <slug>-brand
abu seed "$U" --from <work>/<chosen>.fixed.json --brief <work>/brand-brief.md \
    --mark <work>/<chosen>.mark.svg --board <work>/<chosen>.png
~/.freedom/bin/freedom-lib run .agents/lib/freedom-brand.mjs emit --universe "$U" --surface artifact
```

- Write `brand-brief.md` first, in the operator's own words from the interview: who the pages are for, the
  three words, what they admire, what they refuse, what was already theirs, and the concept in one line.
  It is what a future session reads before touching the brand.
- `abu seed` writes the palette (with the light accent), type, mark and `marks/favicon.svg` (the tab icon) into canon, declares `identity.surfaces` so a page reads the
  colors by role, and makes the board the register anchor. If it rejects the direction it names the field:
  fix that field in the `.json`, re-render the board, and seed again.
- **Success is the `emit` line** printing the approved ground, text, accent and display. If it does not, do not call the universe done.
  `freedom-lib` picks the newest installed Supersuit plugin that has the file. **If `~/.freedom/bin/freedom-lib` is
  missing, say Supersuit is not installed and skip only the emit check, never the universe.**
- Make it a private repo (`abu init` does not run `git init`):
  `git -C "$U" init -q && git -C "$U" add . && git -C "$U" commit -qm "Seed the brand universe"`, then
  `gh repo create <owner>/<slug>-universe --private --source "$U" --push`.
  **If `gh` is missing, unauthenticated or the name is taken:** say which, say the universe is already valid and
  safe locally (give the path), and offer the repo step as the next move. Do not fail the run.
- **Return the universe path** (and the repo link when there is one), and say where the board and the brief are.

## Refusals

- Never choose for them, and never mark a direction "(Recommended)".
- Never ask what the profile already answers.
- Never ship three palettes on one concept.
- Never call anything golden, or lock a mark, before their yes.
- Never act on a failed step in silence: report it with its action.
- Never invent: no made-up quotes, no claimed influences they did not name.
- A thin brand is said plainly, never padded.

<!-- BEGIN GENERATED: report -->
## When this skill misfires, offer to report it

If this skill did not one-shot (a step failed, a check refused something it should not have, an instruction sent you the wrong way, you fixed its output by hand, or it left out an obvious step), the person running it is the only one who knows, and only right now. Offer once, in one line, to report it. On a yes, run it yourself and never show them the command:

    abu report "<what happened>" --expected "<what should have happened, and why>" --command "<the exact command or ask>" --skill abu:explore-a-personal-brand

Write every field from what you just watched: an issue that says what was expected and how to reproduce it gets fixed, and "it broke" does not. A `check-kit` refusal they believe is wrong is `abu check-kit ... --report`, which attaches the findings and the rule each one broke. It prints a pre-filled GitHub issue and sends nothing: hand them the link to read and submit. Inside Freedom, `freedom:suggest-an-improvement` files it for them. If you maintain ABU itself, fix it through `evolve-abu` instead.
<!-- END GENERATED: report -->
