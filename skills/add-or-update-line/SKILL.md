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

1. **Look first.** `abu lines <universe>`. If the wording, or a near version of it, is already
   there, this is a reword of that line and never a new one.
2. **A new line.** A candidate:
   `abu line-add <universe> --id <kebab-id> --name "<name>" --for "<what it is for>" --text "<the wording>" --audience public,client`
   Golden on arrival, when a person has already said yes: add `--by "<their name>" --verbatim "<their words>"`
   (and `--on YYYY-MM-DD` when the yes was not today).
   The first line in a universe also needs `--approver "<Full Name>"`, once per person whose yes
   counts. Ask who that is; never guess it.
3. **A candidate a person just approved.** `abu line-bless <universe> <id> --by "<name>" --verbatim "<their words>"`.
4. **New words for a golden line.** `abu line-reword <universe> <id> --text "<new wording>" --by "<name>" --verbatim "<their words>"`.
   The old wording moves into the line's history and the version goes up by one. Never delete a
   history entry: an earlier wording is how an out-of-date page gets found.
5. **A line the brand stopped saying.** `abu line-retire <universe> <id> --by "<name>" --verbatim "<their words>" --instead <golden-line-id>`,
   or `--note "<why nothing replaces it>"` when nothing does.
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

## Refusals

- **Never make a line golden on your own reading.** Harvesting, drafting and proposing produce
  candidates. Golden is a person's recorded yes.
- **Never hand-edit the record's `version`, `history` or `decided`.** The verbs keep them true.
- **Never restate a term rule as a line.** Spelling and capitalization live in `identity.voice`.
