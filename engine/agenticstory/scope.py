"""Where a look may be used: a Style Pack's typed `scope`, and a register's typed medium
exception (SPEC §4.7 and §11, v0.62).

Earned 2026-10-15 on continental-works (issue #60). Gary picked an illustrated look for the
three made-up readers of one book, inside a universe whose register is film photography and
rejects "illustration, painting, drawing, vector art, flat art of any kind". Both halves of that
decision could only be written as prose: a free-form `scope` sentence on the pack and an
`exceptions` note on a craft record. Nothing read either, so the pack would have rendered any
subject for any surface, and the register's refusal of illustration was quietly untrue with no
record a gate could check. A ruling no gate reads is an opinion that lasts until the next agent
finds it inconvenient.

The two shapes, both carrying the decision as {by, on, verbatim} like the kit (§13.1):

  pack.json  "scope": {
      "uses":     ["<work-or-surface id>", ...],      # REQUIRED, the only uses allowed
      "subjects": "<who or what it may depict>",       # optional, read by people
      "never":    ["<what it must never depict>"],     # optional, read by people
      "decided":  {"by": "...", "on": "YYYY-MM-DD", "verbatim": "..." | ["...", ...]}}

  universe.json identity.register "exceptions": [{
      "id":        "<kebab id>",
      "medium":    "<the medium allowed INSTEAD of the register's own>",
      "stylePack": "<pack id or universe-relative path>",  # the look it renders through
      "uses":      ["<work-or-surface id>", ...],           # every one must be in the pack's scope
      "decided":   {"by": "...", "on": "YYYY-MM-DD", "verbatim": ...},
      "subjects": "...", "why": "..."}]                     # optional

What reads them:

  - `validate` (via `validate_scopes`): every pack scope in the universe and every exception is
    well formed, every exception's pack exists, carries a typed scope, and that scope covers
    every use the exception names (two records of one decision must agree).
  - `generate.py` (via `use_gate`): a render through a scoped pack, or through a pack a register
    exception names, must say which use it is for (`--use <id>`) and that use must be allowed;
    otherwise it REFUSES before any provider is called. The recipe records the use and the
    exception it rendered under, with who decided it.

`uses` are ids the universe chooses (`<book-or-site>:<role>` reads well). They are deliberately
not `identity.surfaces`, which names colour roles for a renderer, not permissions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

TYPED = ('{"uses": ["<id>", ...], "subjects": "...", "never": [...], '
         '"decided": {"by": "...", "on": "YYYY-MM-DD", "verbatim": "..."}}')


def _nonempty_str(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _str_list(v) -> bool:
    return isinstance(v, list) and bool(v) and all(_nonempty_str(x) for x in v)


def decided_problems(d, where: str) -> list[str]:
    """{by, on, verbatim}: who decided, on what date, in what words. Every gap named."""
    if not isinstance(d, dict):
        return [f"{where}: decided must be {{by, on, verbatim}} (who, when, their words)"]
    out = []
    if not _nonempty_str(d.get("by")):
        out.append(f"{where}: decided.by is missing (who decided)")
    if not (isinstance(d.get("on"), str) and DATE.match(d["on"])):
        out.append(f"{where}: decided.on must be a YYYY-MM-DD date, got {d.get('on')!r}")
    v = d.get("verbatim")
    if not (_nonempty_str(v) or _str_list(v)):
        out.append(f"{where}: decided.verbatim is missing (the words they used, verbatim)")
    return out


def scope_problems(scope, where: str) -> list[str]:
    """Every defect in a pack's `scope`; empty when it is sound."""
    if isinstance(scope, str):
        return [f"{where}: scope is prose, which no gate can read. Since SPEC v0.62 it is "
                f"typed: {TYPED}. Keep the sentence as `subjects`."]
    if not isinstance(scope, dict):
        return [f"{where}: scope must be an object: {TYPED}"]
    out = []
    if not _str_list(scope.get("uses")):
        out.append(f"{where}: scope.uses must list at least one use id (the only uses this "
                   f"pack may render for)")
    if "subjects" in scope and not isinstance(scope["subjects"], str):
        out.append(f"{where}: scope.subjects must be a string")
    if "never" in scope and not (isinstance(scope["never"], list)
                                 and all(isinstance(x, str) for x in scope["never"])):
        out.append(f"{where}: scope.never must be a list of strings")
    out += decided_problems(scope.get("decided"), f"{where}: scope")
    return out


def _pack_dir(root: Path, spec: str) -> Path:
    from .register import pack_dir
    return Path(root) / pack_dir(spec)


def _load(pj: Path):
    try:
        return json.loads(pj.read_text())
    except (OSError, ValueError):
        return None


def exception_problems(root: Path, exc, i: int, seen: set) -> list[str]:
    where = f"identity.register.exceptions[{i}]"
    if not isinstance(exc, dict):
        return [f"{where}: must be an object"]
    eid = exc.get("id")
    if _nonempty_str(eid):
        where = f"identity.register.exceptions[{eid}]"
        if eid in seen:
            return [f"{where}: the id is declared twice"]
        seen.add(eid)
    out = []
    if not _nonempty_str(eid):
        out.append(f"{where}: id is missing")
    if not _nonempty_str(exc.get("medium")):
        out.append(f"{where}: medium is missing (the medium allowed instead of the register's)")
    if not _str_list(exc.get("uses")):
        out.append(f"{where}: uses must list at least one use id")
    out += decided_problems(exc.get("decided"), where)
    spec = exc.get("stylePack")
    if not _nonempty_str(spec):
        out.append(f"{where}: stylePack is missing (the look this exception renders through)")
        return out
    pj = _pack_dir(root, spec) / "pack.json"
    pack = _load(pj)
    if pack is None:
        out.append(f"{where}: stylePack {spec!r} has no readable pack.json at {pj}")
        return out
    sc = pack.get("scope")
    if sc is None:
        out.append(f"{where}: pack {spec!r} has no typed scope, so nothing stops it rendering "
                   f"outside this exception. Give it scope.uses covering {exc.get('uses')}")
    elif isinstance(sc, dict) and _str_list(sc.get("uses")) and _str_list(exc.get("uses")):
        missing = [u for u in exc["uses"] if u not in sc["uses"]]
        if missing:
            out.append(f"{where}: uses {missing} are not in pack {spec!r} scope.uses "
                       f"{sc['uses']}; the two records of one decision disagree")
    return out


def validate_scopes(root: Path, manifest: dict) -> list[str]:
    """Every defect in the universe's pack scopes and register exceptions."""
    root = Path(root)
    out = []
    style = root / "reference" / "style"
    if style.is_dir():
        for pj in sorted(style.rglob("pack.json")):
            pack = _load(pj)
            if isinstance(pack, dict) and "scope" in pack:
                out += scope_problems(pack["scope"], str(pj.parent.relative_to(root)))
    reg = (manifest.get("identity") or {}).get("register")
    if not isinstance(reg, dict) or "exceptions" not in reg:
        return out
    excs = reg.get("exceptions")
    if not isinstance(excs, list):
        return out + ["identity.register.exceptions must be a list"]
    seen: set = set()
    for i, exc in enumerate(excs):
        out += exception_problems(root, exc, i, seen)
    return out


def find_universe(start: Path):
    """The universe root a pack lives in (nearest ancestor with universe.json), or None."""
    p = Path(start).resolve()
    for d in [p, *p.parents]:
        if (d / "universe.json").is_file():
            return d
    return None


def exceptions_naming(pack_dir: Path) -> list[dict]:
    """The register exceptions, in the pack's own universe, that render through this pack."""
    root = find_universe(pack_dir)
    if root is None:
        return []
    uni = _load(root / "universe.json") or {}
    reg = (uni.get("identity") or {}).get("register")
    if not isinstance(reg, dict):
        return []
    me = Path(pack_dir).resolve()
    out = []
    for exc in reg.get("exceptions") or []:
        if isinstance(exc, dict) and _nonempty_str(exc.get("stylePack")):
            if _pack_dir(root, exc["stylePack"]).resolve() == me:
                out.append(exc)
    return out


def use_gate(pack: dict, pack_dir, use):
    """`(problem, record)` for a render through `pack` for `use`.

    `problem` is None when the render may proceed, else the refusal to print. `record` is what
    the recipe carries: `{}` when nothing applies, else `use` and, when a register exception
    governs the pack, `registerException` {id, medium, decided}.
    """
    pid = pack.get("id") or Path(pack_dir).name
    allowed = None
    if "scope" in pack:
        probs = scope_problems(pack["scope"], f"style pack {pid!r}")
        if probs:
            return "generate.py: " + "\n  ".join(probs), {}
        allowed = list(pack["scope"]["uses"])
    excs = exceptions_naming(pack_dir)
    exc_uses = [u for e in excs for u in (e.get("uses") or [])]
    if allowed is None and not excs:
        return None, ({"use": use} if use else {})
    permitted = [u for u in (allowed if allowed is not None else exc_uses)
                 if not excs or u in exc_uses]
    if not use:
        return (f"generate.py: style pack {pid!r} is scoped, so a render must say which use "
                f"it is for: pass --use <id>, one of {permitted}. A scoped look rendered with "
                f"no stated use is how it leaks onto a surface nobody approved it for."), {}
    if use not in permitted:
        why = (f"its scope allows {allowed}" if allowed is not None else "")
        if excs:
            why += (("; " if why else "") + "the register exception(s) "
                    + ", ".join(repr(e.get("id")) for e in excs) + f" allow {exc_uses}")
        return (f"generate.py: --use {use!r} is outside style pack {pid!r}: {why}. Use a "
                f"listed id, or record the new use as a decision first (who, when, their words) "
                f"in the pack's scope and the register exception."), {}
    rec = {"use": use}
    for e in excs:
        if use in (e.get("uses") or []):
            rec["registerException"] = {k: e.get(k) for k in ("id", "medium", "decided")}
            break
    return None, rec
