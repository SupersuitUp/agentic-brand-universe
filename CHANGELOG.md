# Changelog

The npm package `@supersuit/abu` is the ABU engine at the same version as the `abu` Claude plugin;
both are released by one `vX.Y.Z` tag. The full record of every version is [SAVE-LOG.md](./SAVE-LOG.md).

## 1.46.0 (2026-10-14)

- Every ABU skill now ends by offering to report a misfire, not just the front door. The step is one
  generated block (`report`) stamped into each `SKILL.md` by `abu build-docs`, pre-filled with that
  skill's own `--skill abu:<name>`, so a new skill gets it on the next build and a skill without it
  fails the docs gate.
- `build-docs --check` reports a block whose source file is missing instead of crashing.

## 1.45.0 (2026-10-14)

- `abu-allow: <reason>` waives one line in `abu check-kit`, at the end of the line or as a comment by
  itself on the line above. A reason is required; a bare `abu-allow:` waives nothing. Waived lines are
  counted ("clean, 3 waived") and never enter a baseline. For faithful mockups of another product's UI,
  such as an iMessage simulator's iOS blue.
- Every check-kit refusal says how to waive it and how to report it. `--report` prints a pre-filled
  GitHub issue carrying each finding with the rule it broke (refuses, why, instead, who decided it and
  in what words), the command, and the ABU, Python and OS versions.
- `abu report "<what happened>" [--expected] [--command] [--skill] [--details] [--open]` files anything
  ABU got wrong the same way. Nothing is sent until the reporter presses submit.
- The `abu` front door and the steward agent offer the report when a run went wrong, filling every field.

## 1.44.1 (2026-10-14)

- `abu check-kit`'s palette is now the colour VALUES in the kit's `tokensFrom` file (each `hex`, and any
  string that is only a hex), never a hex quoted in prose. The Continental Works record names `#007AFF` in
  a sentence refusing it, and that sentence had put it on the palette, so the refused blue passed.

## 1.44.0 (2026-10-14)

- `abu check-kit --write-baseline <file>` records a surface's existing findings, and `--baseline <file>`
  refuses only new ones (keyed on file, rule, value and line text, so moved code never trips it). This is
  the gate for a CI build, which has no git history to diff against.
- First release published by the version tag alone, through npm trusted publishing.

## 1.43.0 (2026-10-14)

- First npm release. `npm i -D @supersuit/abu` gives any repo the `abu` command, running the bundled
  Python engine (python3 3.9 or later).
- `abu check-kit` refuses off-palette colours (hex, rgb()/rgba(), Tailwind palette classes) against the
  kit's `tokensFrom`, and `--added <range>` judges only the lines a change adds, so a build or a push
  can gate on what it introduces without being blocked by old debt.
