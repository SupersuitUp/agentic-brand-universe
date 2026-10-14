# Changelog

The npm package `@supersuit/abu` is the ABU engine at the same version as the `abu` Claude plugin;
both are released by one `vX.Y.Z` tag. The full record of every version is [SAVE-LOG.md](./SAVE-LOG.md).

## 1.43.0 (2026-10-14)

- First npm release. `npm i -D @supersuit/abu` gives any repo the `abu` command, running the bundled
  Python engine (python3 3.9 or later).
- `abu check-kit` refuses off-palette colours (hex, rgb()/rgba(), Tailwind palette classes) against the
  kit's `tokensFrom`, and `--added <range>` judges only the lines a change adds, so a build or a push
  can gate on what it introduces without being blocked by old debt.
