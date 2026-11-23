"""public_paths.py: the ONE rewrite every recipe meant for a public surface goes through (SPEC §3.2.1).

A recipe records the absolute paths a render was made from, which is right on the machine
that made it and wrong on the open web: a wiki serves the recipe beside its image, and a
home-folder path names the person and their machine. Earned 2026-11-23: the supersuit.wiki
chief-of-agents recipe served 96 `/Users/<name>/...` paths, and its replacement would have
added dead `/private/tmp/<worktree>/...` ones, because compose-strip's export copied the
recipe verbatim.

The rule, applied to every string anywhere in the recipe:

  * a home-folder path (`/Users/<name>/...`, `/home/<name>/...`) becomes `~/...`;
  * a temporary-folder path (`/tmp/...`, `/private/tmp/...`, `/var/folders/.../T/...`) becomes
    a stable repo-relative form, `<repo>/<path inside it>`, when it is inside a git checkout
    that still exists or under a root the caller names; a temp path nothing can resolve keeps
    only its tail as `<tmp>/<name>/...`, which no longer names a machine;
  * the recipe says so, in `publicPaths`, so a reader knows the paths were rewritten for
    publication and where the recipe as recorded lives.

Only the published COPY is rewritten. The recipe beside the work in the universe is the record
and is never touched by this module.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

FIELD = "publicPaths"
RULE = ("home-folder paths written as ~/...; temporary-folder paths written as <repo>/<path> "
        "(or <tmp>/<name>/... when no repo resolves); the recipe as recorded stays with the work")

HOME_RE = re.compile(r"(?<![\w~])/(?:Users|home)/[^/\s\"']+(?=/|$)")
TMP_RE = re.compile(
    r"(?<![\w~])(?:/private)?/(?:tmp|var/folders/[^/\s\"']+/[^/\s\"']+/T)/[^\s\"'(),;]*")


@lru_cache(maxsize=512)
def _git_label(directory: str) -> tuple[str, str] | None:
    """(toplevel, repo name) for a directory inside a live git checkout, else None."""
    try:
        top = subprocess.run(["git", "-C", directory, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
        if top.returncode != 0:
            return None
        toplevel = top.stdout.strip()
        url = subprocess.run(["git", "-C", toplevel, "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        name = re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1].split(":")[-1]) if url else ""
        return toplevel, (name or Path(toplevel).name)
    except (OSError, subprocess.SubprocessError):
        return None


def _variants(p: str) -> list[str]:
    """A temp root and its macOS twin: /tmp is a symlink to /private/tmp."""
    p = p.rstrip("/")
    out = [p]
    if p.startswith("/private/tmp"):
        out.append(p[len("/private"):])
    elif p.startswith("/tmp"):
        out.append("/private" + p)
    return out


def _tmp(path: str, roots: list[tuple[str, str]]) -> str:
    for prefix, label in roots:
        for v in _variants(prefix):
            if path == v or path.startswith(v + "/"):
                return label.rstrip("/") + path[len(v):]
    probe = Path(path)
    while str(probe) not in ("/", "") and not probe.exists():
        probe = probe.parent
    if probe.exists() and str(probe) not in ("/", "/tmp", "/private/tmp"):
        found = _git_label(str(probe if probe.is_dir() else probe.parent))
        if found:
            top, name = found
            real = os.path.realpath(path) if os.path.exists(path) else path
            for base in _variants(top) + _variants(os.path.realpath(top)):
                for cand in (path, real):
                    if cand == base or cand.startswith(base + "/"):
                        return name + cand[len(base):]
    m = re.match(r"(?:/private)?/(?:tmp|var/folders/[^/]+/[^/]+/T)/(.*)", path)
    return "<tmp>/" + (m.group(1) if m else path.lstrip("/"))


def publicize_text(s: str, roots: Mapping[str, str] | None = None) -> str:
    """One string, rewritten by the rule. Idempotent."""
    rl = sorted(((str(k), v) for k, v in (roots or {}).items()), key=lambda kv: -len(kv[0]))
    # Roots first, including roots that are themselves under the home folder, so a caller can
    # name a repo for a checkout wherever it lives.
    for prefix, label in rl:
        for v in _variants(prefix):
            s = re.sub(re.escape(v) + r"(?=/|$|[\s\"'])", label.rstrip("/"), s)
    s = TMP_RE.sub(lambda m: _tmp(m.group(0), rl), s)
    return HOME_RE.sub("~", s)


def _walk(o: Any, roots) -> tuple[Any, int]:
    if isinstance(o, str):
        new = publicize_text(o, roots)
        return new, int(new != o)
    if isinstance(o, list):
        out, n = [], 0
        for v in o:
            nv, c = _walk(v, roots)
            out.append(nv)
            n += c
        return out, n
    if isinstance(o, dict):
        out, n = {}, 0
        for k, v in o.items():
            if k == FIELD:
                out[k] = v
                continue
            nv, c = _walk(v, roots)
            out[k] = nv
            n += c
        return out, n
    return o, 0


def publicize_recipe(recipe: Mapping, roots: Mapping[str, str] | None = None,
                     recorded_at: str | None = None) -> tuple[dict, int]:
    """The recipe rewritten for a public surface, and how many strings changed. Always stamps
    `publicPaths` (with the count), so an exported recipe says it was published this way even
    when nothing needed rewriting."""
    out, n = _walk(dict(recipe), roots)
    prev = (recipe.get(FIELD) or {}) if isinstance(recipe.get(FIELD), dict) else {}
    out[FIELD] = {"by": "agenticstory.public_paths", "rule": RULE,
                  "rewritten": int(prev.get("rewritten", 0)) + n,
                  **({"recordedAt": publicize_text(recorded_at, roots)} if recorded_at
                     else ({"recordedAt": prev["recordedAt"]} if prev.get("recordedAt") else {}))}
    return out, n


def has_private_paths(o: Any) -> bool:
    """True when any string in `o` still carries a home-folder or temporary-folder path."""
    if isinstance(o, str):
        return bool(HOME_RE.search(o) or TMP_RE.search(o))
    if isinstance(o, list):
        return any(has_private_paths(v) for v in o)
    if isinstance(o, dict):
        return any(has_private_paths(v) for k, v in o.items() if k != FIELD)
    return False


def publicize_file(path: Path, roots: Mapping[str, str] | None = None,
                   write: bool = True) -> int:
    """Rewrite one published `.recipe.json` in place. Returns the number of strings changed
    (0 means it was already clean and the file is left byte for byte as it was)."""
    path = Path(path)
    raw = path.read_text()
    recipe = json.loads(raw)
    if not has_private_paths(recipe):
        return 0
    new, n = publicize_recipe(recipe, roots)
    if write and n:
        indent = 1 if raw.startswith("{\n \"") else 2
        path.write_text(json.dumps(new, indent=indent, ensure_ascii=False) + "\n")
    return n
