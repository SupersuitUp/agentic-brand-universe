---
title: "Record one golden line, so the brand's approved language has a typed home and a person's yes on it"
id: HDSOP-ABU-040
version: 0.1
skill: add-or-update-line
doc_status: drafting
tags: [authoring, canon, craft, brand, language]
frequency: "whenever a human rules on wording, and on every harvest of repeated approved sentences"
est_time_per_run: "5 min"
automation_potential: "high"
related_skills: [add-piece-or-no-go, voice-gate, evolve-abu]
related_workflows: []
concepts: [canon, craft-canon, lines, golden-line, approver]
---

# Purpose

The brand's approved sentences live in one typed record, with who said yes, when and in what
words, and every earlier wording kept, so a changed line can be told apart from a stale copy.

# When to use (Trigger)

A human rules on wording ("that's the line", "say it this way from now on", "we don't say that
anymore"), the same approved sentence is about to be pasted into a second surface, or two surfaces
say the same thing in different words.

# Inputs / Prerequisites

- The target universe, and `abu lines <universe>` read first.
- The wording exactly, the audiences it may reach (`public`, `client`, `team`, `cofounder`), and
  for anything golden the person's yes verbatim with its date.
- For the first line in a universe, the people whose yes counts (the approvers).

# Steps

1. `abu lines <universe>`: is the wording already a line?
2. A new line: `abu line-add` (a candidate, or golden with `--by` and `--verbatim`; `--approver`
   once per person on the first line).
3. A candidate a person approved: `abu line-bless`.
4. New words for a golden line: `abu line-reword` (the old wording goes to history, the version
   goes up by one).
5. A line the brand stopped saying: `abu line-retire` with `--instead <golden id>` or `--note`.
6. `abu lines <universe>` to read it back; commit the record file by name.

# Outputs

One changed line in `canon/craft/brand-lines.json`, committed by name. Done means `abu validate
<universe>` prints no line starting `lines ` and `abu lines <universe>` shows the change.

# Failure modes

- Recording an agent's own preference as golden. `validate` refuses it because the approver list
  does not contain the agent; the decision only a human makes is the yes itself and who may give it.
- A second id for a sentence the record already holds (two sources of truth).
- Deleting a history entry (the record can no longer find a page carrying the old wording).
- Hand-editing `version`, `history` or `decided` instead of using the verbs.
