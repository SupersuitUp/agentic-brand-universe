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
  - a golden or retired line carries `decided` {by, on, verbatim} and `by` is an approver: a yes
    from a name the record does not list is refused, so a harvest or a draft stays a candidate.
    A candidate carries no `decided`;
  - `version` is a whole number and `history` holds every earlier wording exactly once, each with
    the date it was replaced and by whom, and no two consecutive versions say the same words;
  - a retired line names the line to use `instead` (golden, or itself retired with its own
    `instead`, in a chain that never loops), or null with an `insteadNote`;
  - no two live lines have the same wording.

What it cannot enforce: that the named person spoke. It checks a name against a list and that
words are recorded. The record is evidence, reviewable in the diff, never proof.

The history is load-bearing beyond the record: Plan 2's scan finds an out-of-date surface by
searching for a line's EARLIER wordings, which is why an old text is never deleted.

And the writers (`add`, `bless`, `reword`, `retire`): the only way a line changes. `select`
chooses the record they change: the universe's one lines record whatever its filename, or the
one `--record` names when there are several. A verb creates a record only when the universe has
none, only at `canon/craft/brand-lines.json`, and never changes `approvers`, so a verb cannot
mint a second record with approvers of its own. `write` puts the result on disk whole or not at
all, re-validates the universe, checks the universe loaded THIS file for the record's id, and
restores the previous bytes when any of that refuses, so no verb leaves a record `validate`
would reject and no verb reports a write nothing validated.

Earned 2026-10-13 on continental-works. Gary: "if you don't create the provenance chain between
surfaces and the goldens, there's the opportunity for drift is just so natural, even for a
two-person team that's evolving quickly."
"""
from __future__ import annotations

import datetime
import json
import os
import re
import tempfile
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


def _date(v: Any) -> bool:
    """A real calendar date written YYYY-MM-DD: 2026-02-30 has the shape and is no day."""
    if not (isinstance(v, str) and DATE.match(v)):
        return False
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        return False
    return True


def records(craft: dict) -> list[dict]:
    """The raw lines records among a store's craft canon, in id order."""
    return [c.raw for c in sorted(craft.values(), key=lambda c: str(c.id)) if c.kind == KIND]


def lines_of(rec: dict) -> list:
    """A record's `lines` when it is a list, else nothing: a hand-edited record may hold anything
    there, and a reader that lists or validates must report that, never raise on it."""
    got = rec.get("lines")
    return got if isinstance(got, list) else []


def names(value: Any) -> list[str]:
    """Whatever a record holds where a list of names belongs, as strings fit to print."""
    if value is None:
        return []
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def all_lines(craft: dict) -> list[dict]:
    return [l for r in records(craft) for l in lines_of(r) if isinstance(l, dict)]


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
    if not _date(d.get("on")):
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
        if not _date(h.get("replacedOn")):
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


def _loops(nxt: dict[str, str]) -> list[list[str]]:
    """Every loop in a map of id -> the id it names, each once, written from its smallest id and
    closed on it (['a', 'b', 'a']). An id naming itself is not reported here; it has its own
    message. Each id is walked once, so a loop can never keep the walk going."""
    out: list[list[str]] = []
    done: set[str] = set()
    for start in sorted(nxt):
        path: list[str] = []
        at = start
        while at in nxt and at not in done and at not in path:
            path.append(at)
            at = nxt[at]
        if at in path:
            loop = path[path.index(at):]
            if len(loop) > 1:
                i = loop.index(min(loop))
                out.append(loop[i:] + loop[:i] + [min(loop)])
        done.update(path)
    return out


def validate_lines(craft: dict) -> list[str]:
    """Every defect across every lines record; empty when there are none (lines are optional)."""
    recs = records(craft)
    out: list[str] = []
    status_of: dict[str, Any] = {}
    home: dict[str, Any] = {}        # line id -> the id of the record that holds it
    nxt: dict[str, str] = {}         # retired line id -> the line id its `instead` names
    for r in recs:
        for l in lines_of(r):
            if isinstance(l, dict) and isinstance(l.get("id"), str) and l["id"] not in status_of:
                status_of[l["id"]] = l.get("status")
                home[l["id"]] = r.get("id", "?")
                if l.get("status") == "retired" and isinstance(l.get("instead"), str):
                    nxt[l["id"]] = l["instead"]
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
                    out.append(f"{where}: 'instead' is missing (the id of a golden or retired line, "
                               f"or null with an insteadNote)")
                elif l["instead"] is None:
                    if not _str(l.get("insteadNote")):
                        out.append(f"{where}: instead is null, so 'insteadNote' must say why nothing replaces it")
                elif not isinstance(l["instead"], str):
                    out.append(f"{where}: instead must be the id of a golden or retired line, or null, "
                               f"got {l['instead']!r}")
                elif l["instead"] == lid:
                    out.append(f"{where}: instead names itself")
                elif status_of.get(l["instead"]) not in ("golden", "retired"):
                    # A retired target is allowed: the line it names may itself have been retired
                    # since, and then ITS instead says where to go. Refusing that left a retired
                    # line no verb could re-point, so the line it named could never be retired.
                    out.append(f"{where}: instead names '{l['instead']}', which is not a golden or retired line")
            elif _str(l.get("text")):
                key = norm(l["text"])
                if key in texts:
                    out.append(f"{where}: has the same text as line '{texts[key]}'; one wording is one line")
                else:
                    texts[key] = lid if isinstance(lid, str) else f"#{i}"
    for loop in _loops(nxt):
        out.append(f"lines {home[loop[0]]} line '{loop[0]}': instead chain loops: {' -> '.join(loop)}")
    return out


def _confine(root: Path, file: str) -> Path:
    """The resolved path of a record file, which must be a .json directly inside
    <root>/canon/craft: the only place the universe's validation reads, so a write can never
    land where nothing checks it."""
    craft = (Path(root) / "canon" / "craft").resolve()
    path = (Path(root) / file).resolve()
    if path.parent != craft or path.suffix != ".json":
        raise LineError(f"the record must be a .json file directly in canon/craft, because that is the only "
                        f"place the universe's validation reads; got {file}")
    return path


def _parse(path: Path, file: str) -> Any:
    """The file's JSON. A file that is not UTF-8 says so, as its own refusal: under a C locale a
    sound record was called invalid JSON, with the advice to remove it."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise LineError(f"{file} could not be read as UTF-8 ({e}); fix its encoding by hand") from e
    try:
        return json.loads(text)
    except ValueError as e:
        raise LineError(f"{file} is not valid JSON ({e}); fix or remove it by hand") from e


def load(root: Path, file: str = DEFAULT_FILE) -> tuple[Path, dict | None]:
    """ONE record file: its path and its parsed content, or None when the file does not exist.
    Which file a verb changes is `select`'s decision; this only reads the one it is given."""
    path = _confine(root, file)
    if not path.is_file():
        return path, None
    rec = _parse(path, file)
    if not isinstance(rec, dict):
        raise LineError(f"{file} must hold a JSON object, not {type(rec).__name__}; fix it by hand")
    if rec.get("kind") != KIND:
        raise LineError(f"{file} is a craft record of kind {rec.get('kind')!r}, not '{KIND}'")
    return path, rec


def existing(root: Path) -> list[Path]:
    """Every lines record file the universe has: each *.json directly in canon/craft holding an
    object of kind `lines`, in filename order. A file that cannot be read or parsed is not this
    function's business and is skipped; the store reports it."""
    craft = (Path(root) / "canon" / "craft").resolve()
    out = []
    for f in sorted(craft.glob("*.json")):
        try:
            got = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(got, dict) and got.get("kind") == KIND:
            out.append(f)
    return out


def _rel(path: Path) -> str:
    return f"canon/craft/{path.name}"


def select(root: Path, file: str | None = None, approvers: list[str] | None = None) -> tuple[Path, dict | None]:
    """The record a writer verb changes, and its content (None only when the universe has no
    lines record at all, with the default path, which is where `line-add` creates the first one).

    A verb never creates a SECOND record and never changes who can approve. Before this rule,
    `--record new.json --approver "An Agent"` made a record whose approver was whoever ran the
    verb, and a golden line in it validated.

      - `file` (--record) must be one of the universe's existing lines records;
      - without it, the one existing record is used whatever its filename, and more than one is
        refused with their names;
      - `approvers` (--approver) is refused when a record already exists, never ignored.
    """
    found = existing(root)
    if file:
        path = _confine(root, file)
        match = [f for f in found if path.exists() and f.samefile(path)]
        if not match:
            if path.is_file():
                _parse(path, file)  # a broken file is refused as what it is
            raise LineError(f"--record selects an existing lines record; {file} is not one. A verb creates "
                            f"the universe's first lines record at {DEFAULT_FILE} and never a second one.")
        path, rec = load(root, _rel(match[0]))
    elif len(found) > 1:
        raise LineError(f"this universe has {len(found)} lines records ({', '.join(_rel(f) for f in found)}); "
                        f"say which one with --record")
    else:
        # None found may still mean the default file exists and is broken: `load` refuses that
        # by name, so the first line is never written over a file somebody has to repair.
        path, rec = load(root, _rel(found[0]) if found else DEFAULT_FILE)
    if rec is not None:
        if "lines" in rec and not isinstance(rec["lines"], list):
            raise LineError(f"{_rel(path)}: 'lines' is not a list; fix the record by hand")
        if approvers:
            raise LineError(f"this universe already has a lines record; its approvers are "
                            f"{', '.join(names(rec.get('approvers'))) or '(none listed)'}. Who can approve is "
                            f"changed by the operator in the record file, never by a verb.")
    return path, rec


def new_record(approvers: list[str], id: str = "brand-lines") -> dict:
    """The universe's first lines record. Its id is the stem of the file it goes in, so the id
    and the filename cannot disagree about which record this is."""
    if not approvers:
        raise LineError("this universe has no lines record yet, so name who can make a line golden: "
                        "--approver \"Full Name\" (repeat it for each person)")
    return {"id": id, "kind": KIND, "name": "The brand's golden lines",
            "summary": "Every approved unit of the brand's language, with who made it golden, when and in "
                       "what words, and every wording it has had. SPEC §13.2.",
            "approvers": list(approvers), "lines": []}


def find(rec: dict, lid: str) -> dict:
    """The line with this id, or LineError."""
    for l in lines_of(rec):
        if isinstance(l, dict) and l.get("id") == lid:
            return l
    raise LineError(f"no line '{lid}' in {rec.get('id')}; `abu lines <universe>` lists them")


def add(rec: dict, *, id: str, name: str, purpose: str, text: str, audiences: list[str],
        decided: dict | None = None) -> dict:
    """A new line: a candidate, or golden when it arrives with a person's yes."""
    if any(isinstance(l, dict) and l.get("id") == id for l in lines_of(rec)):
        raise LineError(f"{rec.get('id')} already has a line '{id}'; reword it with `abu line-reword`")
    line = {"id": id, "name": name, "for": purpose, "status": "golden" if decided else "candidate",
            "text": text, "version": 1, "audiences": list(audiences)}
    if decided:
        line["decided"] = dict(decided)
    rec.setdefault("lines", []).append(line)
    return line


NO_YES = "a yes is --by AND --verbatim: who said it, and their words"


def yes(by: str | None, verbatim: str | None, on: str | None = None) -> dict | None:
    """The `decided` a verb records, or None when no yes was given at all. Half a yes, or one
    made of empty words, is refused: it is the thing the record exists to hold."""
    if by is None and verbatim is None:
        return None
    if not (_str(by) and _str(verbatim)):
        raise LineError(NO_YES)
    return {"by": by, "on": on or datetime.date.today().isoformat(), "verbatim": verbatim}


def bless(rec: dict, lid: str, decided: dict) -> dict:
    if not decided:
        raise LineError(NO_YES)
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
    if line.get("status") == "candidate" and decided:
        # Taking the words and dropping the yes left a candidate the operator believed was golden.
        raise LineError(f"line '{lid}' is a candidate: reword it without a yes, then make it golden with line-bless")
    if norm(text) == norm(line.get("text", "")):
        raise LineError(f"line '{lid}' already has the same wording; a version is a change of words")
    if line.get("status") == "candidate":
        line["text"] = text
        return line
    if line.get("status") != "golden":
        raise LineError(f"line '{lid}' is {line.get('status')}; a retired line is not reworded")
    if not decided:
        raise LineError(f"line '{lid}' is golden, so a new wording needs --by and --verbatim: whose yes, in what words")
    was = line.get("version", 1)
    if not isinstance(was, int) or isinstance(was, bool) or not isinstance(line.get("history", []), list):
        raise LineError(f"line '{lid}' has a version or history the verbs cannot continue; "
                        f"`abu validate` says what is wrong with it")
    line.setdefault("history", []).append({"version": was, "text": line.get("text"),
                                           "replacedOn": decided.get("on"), "replacedBy": decided.get("by")})
    line["version"] = was + 1
    line["text"] = text
    line["decided"] = dict(decided)
    return line


def retire(rec: dict, lid: str, decided: dict, instead: str | None = None, note: str | None = None) -> dict:
    if not decided:
        raise LineError(NO_YES)
    line = find(rec, lid)
    if line.get("status") == "retired":
        raise LineError(f"line '{lid}' is already retired")
    if instead and note:
        raise LineError("a retired line takes --instead or --note, not both")
    if not instead and not (note and note.strip()):
        raise LineError("a retired line names what to say instead: --instead <the id of a golden or retired line>, "
                        "or --note \"why nothing replaces it\"")
    line["status"] = "retired"
    line["decided"] = dict(decided)
    line["instead"] = instead or None
    if not instead:
        line["insteadNote"] = note
    return line


def _put(path: Path, data: bytes) -> None:
    """The file holds `data`, whole, or it is exactly as it was: the bytes go to a temp file in
    the same directory and are moved into place in one step. Writing in place truncated the
    record first, so a write that failed halfway left an empty file behind "nothing was written"."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write(root: Path, path: Path, rec: dict) -> list[str]:
    """Put the record on disk and re-validate the universe. On ANY lines problem the previous
    bytes are restored (or the new file removed) and the problems are returned: an empty list
    means the record was written, the universe loaded THIS file for the record's id, and it
    validates. A write that cannot land raises LineError with the file untouched."""
    from .store import CanonStore
    before = path.read_bytes() if path.is_file() else None
    try:
        data = (json.dumps(rec, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        _put(path, data)
    except (OSError, ValueError) as e:
        raise LineError(f"{_rel(path)} could not be written ({type(e).__name__}: {e})") from e
    problems = None
    try:
        store = CanonStore(root)
        rid = rec.get("id", "")
        loaded = store.craft.get(rid)
        shadowed = any(c[0] == rid for c in store.craft_collisions)
        problems = validate_lines(store.craft)
        if shadowed or loaded is None or loaded.raw != rec:
            # Validation above read whatever the store loaded for this id. If that is another
            # file's record, nothing has checked the one just written.
            problems.insert(0, f"lines {rid}: {path.name} is not the record the universe loaded for this id "
                               f"(another file declares the same id)")
    finally:
        if problems is None or problems:
            if before is None:
                path.unlink(missing_ok=True)
            else:
                try:
                    _put(path, before)
                except OSError:
                    path.write_bytes(before)
    return problems
