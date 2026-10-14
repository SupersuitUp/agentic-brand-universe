---
name: add-or-update-line
description: Record ONE golden line (one approved unit of a brand's language - a tagline, the one-sentence answer to "what is this", a positioning paragraph, a credential, a definition) into a universe's lines record (SPEC 13.2, craft-canon kind `lines`), or change one - bless a candidate, give a golden line new words while keeping every earlier wording, or retire it naming what to say instead - always with who said yes, when and in what words. Use the moment a human rules on wording ("that's the line", "say it this way from now on", "we don't say that anymore", "make that the tagline", "that's golden"), when you are about to paste the same approved sentence into a second surface, or when you find two surfaces saying the same thing in different words. Generic and universe-parameterized: pass the target universe. NOT for a single term's spelling or capitalization (that is `identity.voice`, enforced by voice-gate) and NOT for a visual part (add-piece-or-no-go).
---

# Add or update a golden line

A brand's approved language is a set of small units a person said yes to. This skill puts ONE of
them into the universe's lines record, or changes one, through the engine's verbs. It never edits
the record file by hand and it never writes a surface: finding and updating the pages that carry a
line is the lines check, which reads this record.

## Inputs

- The target universe (a path containing `universe.json`). Run `abu lines <universe>` first: the
  wording may already be a line, and a second id for one sentence is the drift this record exists
  to stop.
- The wording, exactly.
- For anything golden: the person's yes, in their own words, and the date. No verbatim means no
  yes. A line nobody has approved is a candidate, and a candidate is a fine thing to record.
- Who may hear it: any of `public`, `client`, `team`, `cofounder`.

## Method

`abu <verb>` is the engine CLI. When `abu` is not on PATH, run the same verb from the engine
directory: `(cd "$ABU/engine" && python3 -m agenticstory.cli <verb> ...)`.

1. **Look first.** `abu lines <universe>`. If the wording, or a near version of it, is already
   there, this is a reword of that line and never a new one.
2. **A new line.** A candidate:
   `abu line-add <universe> --id <kebab-id> --name "<name>" --for "<what it is for>" --text "<the wording>" --audience public,client`
   Golden on arrival, when a person has already said yes: add `--by "<their name>" --verbatim "<their words>"`
   (and `--on YYYY-MM-DD` when the yes was not today).
   The first line in a universe also needs `--approver "<Full Name>"`, once per person whose yes
   counts. Ask who that is; never guess it. That first `line-add` creates
   `canon/craft/brand-lines.json`. After it `--approver` is refused: a verb never changes who can
   approve and never creates a second record.
3. **A candidate a person just approved.** `abu line-bless <universe> <id> --by "<name>" --verbatim "<their words>"`.
4. **New words for a golden line.** `abu line-reword <universe> <id> --text "<new wording>" --by "<name>" --verbatim "<their words>"`.
   The old wording moves into the line's history and the version goes up by one. Never delete a
   history entry: an earlier wording is how an out-of-date page gets found. A candidate is
   reworded with `--text` alone; it takes its yes from `line-bless`.
5. **A line the brand stopped saying.** `abu line-retire <universe> <id> --by "<name>" --verbatim "<their words>" --instead <line-id>`,
   or `--note "<why nothing replaces it>"` when nothing does. `--instead` names a golden line.
   It may name a retired one, whose own `instead` then says where to go; a line that was named
   as someone's `instead` can itself be retired later.
6. **Read back what changed** with `abu lines <universe>`, and commit the record file by name.

## What the verbs refuse, and what to do

- **"not one of this record's approvers"**: the yes came from someone the record does not list.
  Record the line as a candidate and put it in front of an approver. Never add a name to
  `approvers` to get past this; who can approve is the operator's call.
- **"same wording"**: the new text differs only in spacing, quotation marks or emphasis. Nothing
  changed, so there is nothing to record.
- **"has the same text as line ..."**: the sentence is already a line under another id. Use that one.
- **"nothing was written, because the record would not validate"**: the listed defects are in the
  record as it stood plus your change. Fix the change. The file on disk is untouched.
- **"must be a .json file directly in canon/craft"**: `--record` named a file the universe's validation does not read. Leave `--record` off unless the universe keeps more than one lines record.
- **"--record selects an existing lines record; <file> is not one. A verb creates the universe's
  first lines record at canon/craft/brand-lines.json and never a second one."**: `--record` only
  chooses among records that already exist. Drop it.
- **"this universe has N lines records (...); say which one with --record"**: the operator keeps
  more than one. Ask which record the line belongs in and pass that file.
- **"this universe already has a lines record; its approvers are ... Who can approve is changed
  by the operator in the record file, never by a verb."**: you passed `--approver` to a universe
  that has a record. Drop it. If the yes came from someone not listed, the line is a candidate.
- **"a yes is --by AND --verbatim: who said it, and their words"**: one of the two is missing or
  empty. Without the person's words there is no yes; record a candidate.
- **"is a candidate: reword it without a yes, then make it golden with line-bless"**: you gave
  `--by` while rewording a candidate. Reword first, bless second.
- **"instead names '<id>', which is not a golden or retired line"**: the replacement is a
  candidate or does not exist. Bless it first, or name another line.
- **"instead chain loops: a -> b -> a"**: the retired lines point at each other in a circle, so
  none of them says what to use. Point the last one at a golden line, or use `--note`.
- **"is not the record the universe loaded for this id (another file declares the same id)"**:
  two files in `canon/craft` carry one record id, so nothing checked the write. Stop and tell the
  operator; which file is the record is their call. `abu validate` names both files.
- **"could not be read as UTF-8"** or **"nothing was written: ... could not be written"**: the
  record file itself is the problem (its encoding, or the disk). The file is as it was. Tell the
  operator; never delete or recreate the record.

## Refusals

- **Never make a line golden on your own reading.** Harvesting, drafting and proposing produce
  candidates. Golden is a person's recorded yes.
- **Never compose `--verbatim`.** It is the person's actual words. The engine can check that a
  name is on the list; it cannot check that the person spoke. If you do not have their words, the
  line is a candidate.
- **Never pass `--approver` for a name the operator did not give you, and never to a universe
  that already has a lines record.** Who can approve is the operator's decision, made once.
- **Never hand-edit the record's `version`, `history`, `decided` or `approvers`.** The verbs keep
  the first three true, and `approvers` is the operator's to change.
- **Never restate a term rule as a line.** Spelling and capitalization live in `identity.voice`.

<!-- BEGIN GENERATED: report -->
## When this skill misfires, offer to report it

If this skill did not one-shot (a step failed, a check refused something it should not have, an instruction sent you the wrong way, you fixed its output by hand, or it left out an obvious step), the person running it is the only one who knows, and only right now. Offer once, in one line, to report it. On a yes, run it yourself and never show them the command:

    abu report "<what happened>" --expected "<what should have happened, and why>" --command "<the exact command or ask>" --skill abu:add-or-update-line

Write every field from what you just watched: an issue that says what was expected and how to reproduce it gets fixed, and "it broke" does not. A `check-kit` refusal they believe is wrong is `abu check-kit ... --report`, which attaches the findings and the rule each one broke. It prints a pre-filled GitHub issue and sends nothing: hand them the link to read and submit. Inside Freedom, `freedom:suggest-an-improvement` files it for them. If you maintain ABU itself, fix it through `evolve-abu` instead.
<!-- END GENERATED: report -->
