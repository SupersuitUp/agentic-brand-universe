# Changelog

The npm package `@supersuit/abu` is the ABU engine at the same version as the `abu` Claude plugin;
both are released by one `vX.Y.Z` tag. The full record of every version is [SAVE-LOG.md](./SAVE-LOG.md).

## 1.49.1 (2026-10-20)

- `explore-a-personal-brand`: when a site has its own vector logo, the "site is the brand" direction
  now uses it as the mark, on a tile of whichever palette colour it reads against, instead of drawing
  a lettered monogram in its place. A wordmark wider than 2:1 keeps the monogram (it vanishes at
  favicon size) and the direction's sources say why. Found rehearsing on a real site.

## 1.49.1 (2026-10-20)

- `explore-a-personal-brand`: when a site has its own vector logo, the "site is the brand" direction
  now uses it as the mark, on a tile of whichever palette colour it reads against, instead of drawing
  a lettered monogram in its place. A wordmark wider than 2:1 keeps the monogram (it vanishes at
  favicon size) and the direction's sources say why. Found rehearsing on a real site.

## 1.49.0 (2026-10-20)

- New skill `explore-a-personal-brand`: a personal brand exploration that ends in a seeded universe.
  It asks where the operator is starting from (a site that is them, a site that is not, or nothing,
  the default), runs a short voice interview, renders three directions as brand boards in code
  (palette, type, an outlined monogram, a sample page), puts them side by side on the operator's
  phone, refines until they say yes, then writes the universe. Nothing is golden before that yes.
- `abu seed <universe> --from <direction.json>`: writes palette, type, `identity.surfaces`
  (`default`, `artifact`, `artifact-light`), the mark, a favicon, and the brand brief, each with a
  recipe, so `freedom-brand.mjs emit --surface artifact` feeds a self-hosted artifact hub. Inputs are
  validated before anything is written; marks are sanitized.
- Scripts in the skill: `read-site.mjs` (reads a live site's brand in headless Chrome, main-frame
  status only, exit 3 for a thin brand), `render-board.mjs` (board PNG, contrast fixes persisted to
  `<name>.fixed.json`, light-mode accent derived), monogram outlines via `uv run` with pinned
  fonttools.
- Fix: `make-a-book`, `book-doctor` and `land-work` found ABU through a cache path that never
  existed (`cache/garysheng/abu`); they now use `${CLAUDE_PLUGIN_ROOT}` or the newest
  `cache/*/abu/*/`.
- `canon/craft/*.recipe.json` sidecars are no longer loaded as craft records.

## 1.48.0 (2026-10-16)

- `abu check-share <site> [--added <range>]`: refuses a page that would not unfurl as itself, one that
  names no share card or wears another page's card. Any site, no universe needed (Next.js App Router
  and plain HTML). `--added` judges only new pages; `Share-Waiver: <why>` in a commit lets a
  deliberate exception through. Earned when continentalworks.ai/supersuit/computer shipped wearing
  /supersuit's card while every size and URL check passed. SPEC v0.63.

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
