"""Where a provider finds its API key: the flag, then the environment, then the credentials file.

Issue #61, 2026-10-15. The first `abu:explore` render failed with no image because the OpenAI key
lived only in the operator's credentials file (`~/.agents/.env/credentials.env`, the sanctioned
home for keys on a Supersuit machine) and the provider read only the environment. A session that
was never started with the key exported could not draw anything until somebody loaded it by hand.

Order, first non-empty value wins:

  1. `--api-key` passed to the provider
  2. the environment variable (`OPENAI_API_KEY`, `GEMINI_API_KEY`)
  3. the same variable in `$ABU_CREDENTIALS_FILE`, default `~/.agents/.env/credentials.env`

Two refusals, both deliberate:

* **A value is never printed.** Not in a success line, not in an error, not truncated. A printed
  key lands in a transcript on disk and in the model's context, and then it needs rotating.
  `resolve_key` returns where it came from so a caller can say THAT, never what.
* **Only the one named variable is read**, by exact name. The file is never exported wholesale
  into the process, because it holds every other credential on the machine too, and a provider
  that needs one key has no business carrying the rest into a subprocess.

Stdlib only, so it imports inside any provider's PEP 723 environment.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

DEFAULT_FILE = "~/.agents/.env/credentials.env"
FILE_ENV = "ABU_CREDENTIALS_FILE"


def credentials_file() -> Path:
    return Path(os.environ.get(FILE_ENV) or DEFAULT_FILE).expanduser()


def _read_var(name: str, path: Path) -> str | None:
    """The value of exactly `name` in a dotenv-style file, or None. Never raises."""
    pat = re.compile(r"^\s*(?:export\s+)?" + re.escape(name) + r"\s*=(.*)$")
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    for line in lines:
        m = pat.match(line)
        if not m:
            continue
        v = m.group(1).strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        return v or None
    return None


def resolve_key(name: str, provided: str | None = None) -> tuple[str | None, str | None]:
    """`(value, source)`. `source` is "--api-key", "environment", the file's path, or None.

    The source is safe to print. The value never is.
    """
    if provided:
        return provided, "--api-key"
    v = os.environ.get(name)
    if v:
        return v, "environment"
    path = credentials_file()
    v = _read_var(name, path)
    if v:
        return v, str(path)
    return None, None


def missing_message(name: str) -> str:
    path = credentials_file()
    where = "exists but has no value for it" if path.exists() else "does not exist"
    return (f"Error: {name} is not set. It is not in the environment, and {path} {where}.\n"
            f"  Put it in either place: add a line `{name}=...` to {path} (the operator's "
            f"credentials file; `freedom:manage-api-keys` does this without the key ever "
            f"touching the chat), or export {name} before running. Or pass --api-key. "
            f"Set {FILE_ENV} to read a different file.")
