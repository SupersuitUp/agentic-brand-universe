"""Golden lines (SPEC §13.2, v0.61): a universe's approved LANGUAGE, as a validated record.

A golden line is one approved unit of wording: a tagline, the one-sentence answer to "what is
this", a positioning paragraph, a credential, a definition. A person made it golden, and the
record says who, when and in what words, exactly as the kit (§13.1) does for a visual piece.

Before v0.61 a universe held words only as single TERMS (`identity.voice`). An approved sentence
had no typed home, so it lived wherever it was last typed, every other page that said the same
thing was a copy with no link back, and a changed wording reached none of them.

What this module enforces, in `validate` (every defect at once):

  - a record names its `approvers`, the people whose yes makes a line golden;
  - every line has an id, a name, what it is FOR, its `text`, a `status` (candidate, golden,
    retired) and the `audiences` it may appear in front of;
  - a golden or retired line carries `decided` {by, on, verbatim} and `by` is an approver, so an
    agent's harvest can never make a line golden; a candidate carries none;
  - `version` is a whole number and `history` holds every earlier wording exactly once, each with
    the date it was replaced and by whom, and no two consecutive versions say the same words;
  - a retired line names the golden line to use `instead`, or null with an `insteadNote`;
  - no two live lines have the same wording.

The history is load-bearing beyond the record: Plan 2's scan finds an out-of-date surface by
searching for a line's EARLIER wordings, which is why an old text is never deleted.

And the writers (`add`, `bless`, `reword`, `retire`): the only way a line changes. `write` puts
the result on disk, re-validates the universe, and restores the previous bytes when validation
refuses, so no verb leaves a record `validate` would reject.

Earned 2026-10-13 on continental-works. Gary: "if you don't create the provenance chain between
surfaces and the goldens, there's the opportunity for drift is just so natural, even for a
two-person team that's evolving quickly."
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

KIND = "lines"
STATUSES = ("candidate", "golden", "retired")
AUDIENCES = ("public", "client", "team", "cofounder")
DEFAULT_FILE = "canon/craft/brand-lines.json"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', " ": " "})


class LineError(ValueError):
    """A change a writer refuses before touching the record."""


def norm(text: str) -> str:
    """A wording with everything that is not wording removed: line breaks and runs of space,
    curly quotation marks, markdown emphasis, and the link around a linked word. Case is kept,
    because a capital is part of how a brand writes a word."""
    s = str(text).translate(_QUOTES)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*_`]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def records(craft: dict) -> list[dict]:
    """The raw lines records among a store's craft canon, in id order."""
    return [c.raw for c in sorted(craft.values(), key=lambda c: c.id) if c.kind == KIND]


def all_lines(craft: dict) -> list[dict]:
    return [l for r in records(craft) for l in (r.get("lines") or []) if isinstance(l, dict)]


def _check_decided(where: str, line: dict, approvers: list[str]) -> list[str]:
    d = line.get("decided")
    if not isinstance(d, dict):
        return [f"{where}: 'decided' is missing (who made it golden, on what date, in what words)"]
    out = []
    if not _str(d.get("by")):
        out.append(f"{where}: decided.by is missing")
    elif approvers and d["by"] not in approvers:
        out.append(f"{where}: decided.by {d['by']!r} is not one of this record's approvers "
                   f"({', '.join(approvers)}); only an approver makes a line golden")
    if not isinstance(d.get("on"), str) or not DATE.match(d.get("on", "")):
        out.append(f"{where}: decided.on must be a YYYY-MM-DD date, got {d.get('on')!r}")
    if not _str(d.get("verbatim")):
        out.append(f"{where}: decided.verbatim is missing; a line with no recorded yes is a candidate")
    return out


def _check_versions(where: str, line: dict) -> list[str]:
    v = line.get("version")
    if not isinstance(v, int) or isinstance(v, bool) or v < 1:
        return [f"{where}: version must be a whole number, 1 or more, got {v!r}"]
    hist = line.get("history")
    if hist is None:
        hist = []
    if not isinstance(hist, list):
        return [f"{where}: history must be a list"]
    out, got, good = [], [], []
    for h in hist:
        if not isinstance(h, dict):
            out.append(f"{where}: each history entry is {{version, text, replacedOn, replacedBy}}, got {h!r}")
            continue
        n = h.get("version")
        got.append(n)
        if not _str(h.get("text")):
            out.append(f"{where}: history v{n} has no text")
        if not isinstance(h.get("replacedOn"), str) or not DATE.match(h.get("replacedOn", "")):
            out.append(f"{where}: history v{n} replacedOn must be a YYYY-MM-DD date, got {h.get('replacedOn')!r}")
        if not _str(h.get("replacedBy")):
            out.append(f"{where}: history v{n} has no replacedBy")
        if isinstance(n, int) and not isinstance(n, bool) and _str(h.get("text")):
            good.append((n, h["text"]))
    ints = all(isinstance(n, int) and not isinstance(n, bool) for n in got)
    if not ints or sorted(got) != list(range(1, v)):
        out.append(f"{where}: is at version {v}, so history must hold versions 1 to {v - 1} once each, got {got}")
    chain = [t for _, t in sorted(good)] + ([line["text"]] if _str(line.get("text")) else [])
    if any(norm(a) == norm(b) for a, b in zip(chain, chain[1:])):
        out.append(f"{where}: two consecutive versions have the same wording; a version is a change of words")
    return out


def validate_lines(craft: dict) -> list[str]:
    """Every defect across every lines record; empty when there are none (lines are optional)."""
    recs = records(craft)
    out: list[str] = []
    status_of: dict[str, Any] = {}
    for r in recs:
        for l in r.get("lines") or []:
            if isinstance(l, dict) and isinstance(l.get("id"), str):
                status_of.setdefault(l["id"], l.get("status"))
    seen: dict[str, str] = {}
    texts: dict[str, str] = {}
    for r in recs:
        rid = r.get("id", "?")
        approvers = r.get("approvers")
        if not (isinstance(approvers, list) and approvers and all(_str(a) for a in approvers)):
            out.append(f"lines {rid}: 'approvers' must list at least one person whose yes makes a line golden")
            approvers = []
        lines = r.get("lines")
        if not isinstance(lines, list):
            out.append(f"lines {rid}: needs a 'lines' list (it may be empty)")
            continue
        for i, l in enumerate(lines):
            if not isinstance(l, dict):
                out.append(f"lines {rid}: line #{i} must be an object")
                continue
            lid = l.get("id")
            where = f"lines {rid} line '{lid}'" if lid else f"lines {rid} line #{i}"
            if not isinstance(lid, str) or not ID.match(lid):
                out.append(f"{where}: id must be kebab-case")
            elif lid in seen:
                out.append(f"{where}: id is already used in lines {seen[lid]}")
            else:
                seen[lid] = rid
            for f in ("name", "for", "text"):
                if not _str(l.get(f)):
                    out.append(f"{where}: '{f}' is missing")
            status = l.get("status")
            if status not in STATUSES:
                out.append(f"{where}: status must be one of {', '.join(STATUSES)}, got {status!r}")
            out += _check_versions(where, l)
            aud = l.get("audiences")
            if not (isinstance(aud, list) and aud):
                out.append(f"{where}: 'audiences' must name at least one of {', '.join(AUDIENCES)}")
            else:
                for a in aud:
                    if a not in AUDIENCES:
                        out.append(f"{where}: audience {a!r} is not one of {', '.join(AUDIENCES)}")
            if status in ("golden", "retired"):
                out += _check_decided(where, l, approvers)
            elif status == "candidate" and l.get("decided") is not None:
                out.append(f"{where}: a candidate carries no 'decided'; a person's yes makes it golden (abu line-bless)")
            if status == "retired":
                if "instead" not in l:
                    out.append(f"{where}: 'instead' is missing (a golden line's id, or null with an insteadNote)")
                elif l["instead"] is None:
                    if not _str(l.get("insteadNote")):
                        out.append(f"{where}: instead is null, so 'insteadNote' must say why nothing replaces it")
                elif not isinstance(l["instead"], str):
                    out.append(f"{where}: instead must be a golden line's id or null, got {l['instead']!r}")
                elif l["instead"] == lid:
                    out.append(f"{where}: instead names itself")
                elif status_of.get(l["instead"]) != "golden":
                    out.append(f"{where}: instead names '{l['instead']}', which is not a golden line")
            elif _str(l.get("text")):
                key = norm(l["text"])
                if key in texts:
                    out.append(f"{where}: has the same text as line '{texts[key]}'; one wording is one line")
                else:
                    texts[key] = lid if isinstance(lid, str) else f"#{i}"
    return out


def load(root: Path, file: str = DEFAULT_FILE) -> tuple[Path, dict | None]:
    """The record file's path and its parsed content, or None when the file does not exist.
    The file must be a .json directly inside <root>/canon/craft, the only place the universe's
    validation reads, so a write can never land where nothing checks it."""
    craft = (Path(root) / "canon" / "craft").resolve()
    path = (Path(root) / file).resolve()
    if path.parent != craft or path.suffix != ".json":
        raise LineError(f"the record must be a .json file directly in canon/craft, because that is the only "
                        f"place the universe's validation reads; got {file}")
    if not path.is_file():
        return path, None
    try:
        rec = json.loads(path.read_text())
    except ValueError as e:
        raise LineError(f"{file} is not valid JSON ({e}); fix or remove it by hand") from e
    if not isinstance(rec, dict):
        raise LineError(f"{file} must hold a JSON object, not {type(rec).__name__}; fix it by hand")
    if rec.get("kind") != KIND:
        raise LineError(f"{file} is a craft record of kind {rec.get('kind')!r}, not '{KIND}'")
    return path, rec


def new_record(approvers: list[str]) -> dict:
    if not approvers:
        raise LineError("this universe has no lines record yet, so name who can make a line golden: "
                        "--approver \"Full Name\" (repeat it for each person)")
    return {"id": "brand-lines", "kind": KIND, "name": "The brand's golden lines",
            "summary": "Every approved unit of the brand's language, with who made it golden, when and in "
                       "what words, and every wording it has had. SPEC §13.2.",
            "approvers": list(approvers), "lines": []}


def find(rec: dict, lid: str) -> dict:
    """The line with this id, or LineError."""
    for l in rec.get("lines") or []:
        if isinstance(l, dict) and l.get("id") == lid:
            return l
    raise LineError(f"no line '{lid}' in {rec.get('id')}; `abu lines <universe>` lists them")


def add(rec: dict, *, id: str, name: str, purpose: str, text: str, audiences: list[str],
        decided: dict | None = None) -> dict:
    """A new line: a candidate, or golden when it arrives with a person's yes."""
    if any(isinstance(l, dict) and l.get("id") == id for l in rec.get("lines") or []):
        raise LineError(f"{rec.get('id')} already has a line '{id}'; reword it with `abu line-reword`")
    line = {"id": id, "name": name, "for": purpose, "status": "golden" if decided else "candidate",
            "text": text, "version": 1, "audiences": list(audiences)}
    if decided:
        line["decided"] = dict(decided)
    rec.setdefault("lines", []).append(line)
    return line


def bless(rec: dict, lid: str, decided: dict) -> dict:
    line = find(rec, lid)
    if line.get("status") != "candidate":
        raise LineError(f"line '{lid}' is {line.get('status')}, not a candidate; nothing to bless")
    line["status"] = "golden"
    line["decided"] = dict(decided)
    return line


def reword(rec: dict, lid: str, text: str, decided: dict | None = None) -> dict:
    """New words. A candidate is a draft and is simply replaced. A golden line keeps its old
    wording in `history`, goes up one version, and takes the new yes as its `decided`."""
    line = find(rec, lid)
    if norm(text) == norm(line.get("text", "")):
        raise LineError(f"line '{lid}' already has the same wording; a version is a change of words")
    if line.get("status") == "candidate":
        line["text"] = text
        return line
    if line.get("status") != "golden":
        raise LineError(f"line '{lid}' is {line.get('status')}; a retired line is not reworded")
    if not decided:
        raise LineError(f"line '{lid}' is golden, so a new wording needs --by and --verbatim: whose yes, in what words")
    line.setdefault("history", []).append({"version": line.get("version", 1), "text": line["text"],
                                           "replacedOn": decided.get("on"), "replacedBy": decided.get("by")})
    line["version"] = line.get("version", 1) + 1
    line["text"] = text
    line["decided"] = dict(decided)
    return line


def retire(rec: dict, lid: str, decided: dict, instead: str | None = None, note: str | None = None) -> dict:
    line = find(rec, lid)
    if line.get("status") == "retired":
        raise LineError(f"line '{lid}' is already retired")
    if instead and note:
        raise LineError("a retired line takes --instead or --note, not both")
    if not instead and not (note and note.strip()):
        raise LineError("a retired line names what to say instead: --instead <a golden line's id>, "
                        "or --note \"why nothing replaces it\"")
    line["status"] = "retired"
    line["decided"] = dict(decided)
    line["instead"] = instead or None
    if not instead:
        line["insteadNote"] = note
    return line


def write(root: Path, path: Path, rec: dict) -> list[str]:
    """Put the record on disk and re-validate the universe. On ANY lines problem the previous
    bytes are restored (or the new file removed) and the problems are returned: an empty list
    means the record was written and validates."""
    from .store import CanonStore
    before = path.read_bytes() if path.is_file() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    try:
        problems = validate_lines(CanonStore(root).craft)
    except BaseException:
        problems = None
        raise
    finally:
        if problems is None or problems:
            if before is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(before)
    return problems
