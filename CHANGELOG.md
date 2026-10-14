# Changelog

The npm package `@supersuit/abu` is the ABU engine at the same version as the `abu` Claude plugin;
both are released by one `vX.Y.Z` tag. The full record of every version is [SAVE-LOG.md](./SAVE-LOG.md).

## Unreleased

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
