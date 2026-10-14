"""The kit (SPEC §13.1, v0.60): a universe's catalog of brand PIECES and NO-GOS.

A piece is a reusable part of the brand with an exact recipe (the selection ring, the six-stripe
thread, the primary button). A no-go is a thing the brand refuses, with the piece to use instead.
Both carry who decided them, when, and in what words, because a refusal with no provenance is an
opinion and gets re-litigated by the next agent that finds it inconvenient.

Before v0.60 a universe had nowhere typed to put either. Pieces lived as sentences inside
register-rule records (or only in site code), and no-gos were scattered across rule prose,
icon notes and project STATE files, so nothing could READ them: no gate refused a surface that
used a refused shape, and a ruling stayed true only for as long as somebody remembered it.

What this module enforces, in `validate` (every defect at once, like `identity.surfaces`):

  - every piece has an id, a name, what it is FOR, and either a `recipe` or a `definedAt`
    pointer into existing canon (a pointer, so a piece already defined is never duplicated);
  - every no-go has an id, what it `refuses`, `why`, and `instead` (a piece id in a kit, or
    null with an `insteadNote` saying why there is no replacement);
  - every item carries `decided` {by, on, verbatim} and, where it was HARVESTED from canon, a
    `source` whose `quote` must still be present at the pointer it cites, so a no-go cannot
    outlive the canon line it was lifted from without the gate saying so;
  - a `supersedes` entry names a live canon line and the words it used to `said`; those words
    must be GONE from that line, because a ruling recorded here while canon still says the old
    thing is two sources of truth disagreeing;
  - a recipe naming tokens is checked against the kit's `tokensFrom` map;
  - every `detect` pattern compiles, because the gate skips what it cannot read.

And `scan`: run every no-go's `detect` patterns over a surface's SOURCE files, which is how a
no-go becomes a refusal rather than a remembered preference (`abu check-kit`).

And `off_palette` (2026-10-14): every colour literal in a surface's source that the
universe's token file does not hold. The palette is every colour VALUE in the file a kit's
`tokensFrom` names (the tokens and whatever the record derives from them, never a hex quoted in
prose, which is usually a colour the record refuses) plus white, so a new
colour is a decision made in canon first, never typed into a surface. And `added_lines`, which lets
a gate judge only what a change ADDS, so a surface carrying old debt can still ship clean work:
Gary, 2026-10-14, "The cw plugin should have a guard for pushing any cw surface without consulting
Abu", after a session restyled a page in hand-picked shadows and a black ring.

Earned 2026-10-06 on continental-works: Gary rejected the six stripes run down one edge of a
selected card ("I really don't like it when you ... use the stripes like the way you did it for
Diane") and asked that the replacement "be part of the ABU, as like, I think the ABU should be
cataloging all these different Lego pieces of the brand and no-goes".
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

KIND = "kit"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# A source in a SIBLING repo is written "<repo>:<path>" (optionally "@<commit>"). It is recorded,
# not checked: the sibling may be on any branch, and a gate that fails on someone else's checkout
# is a gate people learn to skip.
SIBLING = re.compile(r"^[A-Za-z0-9_.-]+:(?!//)")
SKIP_DIRS = {"node_modules", ".git", ".next", "dist", "build", "out", ".docusaurus",
             ".turbo", ".vercel", ".cache", "__pycache__", "coverage"}
DEFAULT_FILES = ["*.css", "*.scss", "*.sass", "*.less", "*.html", "*.htm", "*.js", "*.mjs",
                 "*.cjs", "*.ts", "*.tsx", "*.jsx", "*.vue", "*.svelte", "*.astro"]
MAX_BYTES = 2_000_000


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _text(v: Any) -> str:
    """Everything a pointer resolves to, flattened to one searchable string."""
    if isinstance(v, str):
        return v
    if isinstance(v, (list, tuple)):
        return " ".join(_text(x) for x in v)
    if isinstance(v, dict):
        return " ".join(_text(x) for x in v.values())
    return "" if v is None else str(v)


def resolve(root: Path, pointer: str) -> tuple[bool, Any, str]:
    """`<file>#<dot.path>` inside the universe -> (found, value, why-not).

    A numeric segment indexes a list (`rules.4`). No `#` means the whole file. A `.json` file
    is parsed; any other file resolves to its text and takes no path."""
    if not isinstance(pointer, str) or not pointer:
        return False, None, f"pointer must be '<file>#<path>', got {pointer!r}"
    file, _, path = pointer.partition("#")
    f = Path(root) / file
    if not f.is_file():
        return False, None, f"{file} does not exist in the universe"
    if f.suffix != ".json":
        if path:
            return False, None, f"{file} is not JSON, so it takes no '#{path}'"
        return True, f.read_text(errors="replace"), ""
    try:
        obj: Any = json.loads(f.read_text())
    except ValueError:
        return False, None, f"{file} is not valid JSON"
    for seg in [s for s in path.split(".") if s]:
        if isinstance(obj, list) and seg.isdigit() and int(seg) < len(obj):
            obj = obj[int(seg)]
        elif isinstance(obj, dict) and seg in obj:
            obj = obj[seg]
        else:
            return False, None, f"{pointer} does not resolve (no '{seg}')"
    return True, obj, ""


def _as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _check_decided(where: str, item: dict) -> list[str]:
    d = item.get("decided")
    if not isinstance(d, dict):
        return [f"{where}: 'decided' is missing (who ruled, on what date, in what words)"]
    out = []
    if not isinstance(d.get("by"), str) or not d.get("by").strip():
        out.append(f"{where}: decided.by is missing")
    if not isinstance(d.get("on"), str) or not DATE.match(d.get("on", "")):
        out.append(f"{where}: decided.on must be a YYYY-MM-DD date, got {d.get('on')!r}")
    verb = d.get("verbatim")
    has_verbatim = (isinstance(verb, str) and verb.strip()) or (
        isinstance(verb, list) and verb and all(isinstance(x, str) and x.strip() for x in verb))
    if not has_verbatim and not item.get("source"):
        out.append(f"{where}: decided.verbatim is missing and there is no 'source' to cite instead; "
                   "a ruling with neither is an opinion")
    return out


def _check_sources(root: Path, where: str, item: dict) -> list[str]:
    out = []
    for s in _as_list(item.get("source")):
        if not isinstance(s, dict) or not isinstance(s.get("at"), str):
            out.append(f"{where}: each source is {{at, quote}}, got {s!r}")
            continue
        at, quote = s["at"], s.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            out.append(f"{where}: source {at} has no quote; quote the line the no-go was lifted from")
            continue
        if SIBLING.match(at) and not (Path(root) / at.split("#")[0]).exists():
            continue  # a sibling repo's file: recorded, not checked
        ok, val, why = resolve(root, at)
        if not ok:
            out.append(f"{where}: source {why}")
        elif _ws(quote) not in _ws(_text(val)):
            out.append(f"{where}: source {at} no longer says {quote!r}; the canon line moved or "
                       "changed, so re-cite it or retire this item")
    return out


def _check_supersedes(root: Path, where: str, item: dict) -> list[str]:
    out = []
    for s in _as_list(item.get("supersedes")):
        if not isinstance(s, dict) or not isinstance(s.get("at"), str) or not isinstance(s.get("said"), str):
            out.append(f"{where}: each supersedes entry is {{at, said}}, got {s!r}")
            continue
        ok, val, why = resolve(root, s["at"])
        if not ok:
            out.append(f"{where}: supersedes {why}")
        elif _ws(s["said"]) in _ws(_text(val)):
            out.append(f"{where}: supersedes {s['at']}, which STILL says {s['said']!r}; update the "
                       "live line (keep the old words in its own supersession note)")
    return out


def _check_detect(where: str, item: dict) -> list[str]:
    out = []
    for d in _as_list(item.get("detect")):
        if not isinstance(d, dict) or not isinstance(d.get("pattern"), str):
            out.append(f"{where}: each detect entry is {{pattern, files?, note?}}, got {d!r}")
            continue
        try:
            re.compile(d["pattern"], re.I)
        except re.error as e:
            out.append(f"{where}: detect pattern does not compile ({e}): {d['pattern']!r}")
        files = d.get("files")
        if files is not None and not (isinstance(files, list) and all(isinstance(x, str) for x in files)):
            out.append(f"{where}: detect.files must be a list of globs")
    return out


def kits(craft: dict) -> list[dict]:
    """The raw kit records among a store's craft canon, in id order."""
    return [c.raw for c in sorted(craft.values(), key=lambda c: c.id) if c.kind == KIND]


def validate_kits(root: Path, craft: dict) -> list[str]:
    """Every defect across every kit record; empty when there are none (a kit is optional)."""
    root = Path(root)
    records = kits(craft)
    out: list[str] = []
    piece_ids: dict[str, str] = {}
    seen: dict[str, str] = {}
    for k in records:
        for p in k.get("pieces") or []:
            if isinstance(p, dict) and isinstance(p.get("id"), str):
                piece_ids[p["id"]] = k.get("id", "?")
    for k in records:
        kid = k.get("id", "?")
        pieces, nogos = k.get("pieces"), k.get("noGos")
        if not isinstance(pieces, list) or not isinstance(nogos, list):
            out.append(f"kit {kid}: needs 'pieces' and 'noGos' lists (either may be empty)")
            continue
        token_map = None
        if k.get("tokensFrom") is not None:
            ok, val, why = resolve(root, k["tokensFrom"])
            if not ok or not isinstance(val, dict):
                out.append(f"kit {kid}: tokensFrom {why or 'does not name a map of tokens'}")
            else:
                token_map = val
        for kind, items in (("piece", pieces), ("no-go", nogos)):
            for i, it in enumerate(items):
                if not isinstance(it, dict):
                    out.append(f"kit {kid}: {kind} #{i} must be an object")
                    continue
                iid = it.get("id")
                where = f"kit {kid} {kind} '{iid}'" if iid else f"kit {kid} {kind} #{i}"
                if not isinstance(iid, str) or not re.match(r"^[a-z0-9][a-z0-9-]*$", iid):
                    out.append(f"{where}: id must be kebab-case")
                elif iid in seen:
                    out.append(f"{where}: id is already used by {seen[iid]}")
                else:
                    seen[iid] = f"{kind} in kit {kid}"
                out += _check_decided(where, it)
                out += _check_sources(root, where, it)
                out += _check_supersedes(root, where, it)
                if kind == "piece":
                    for f in ("name", "for"):
                        if not isinstance(it.get(f), str) or not it[f].strip():
                            out.append(f"{where}: '{f}' is missing")
                    if not it.get("recipe") and not it.get("definedAt"):
                        out.append(f"{where}: needs a 'recipe' or a 'definedAt' pointer to the canon "
                                   "that already defines it")
                    for ptr in _as_list(it.get("definedAt")):
                        ok, _, why = resolve(root, ptr)
                        if not ok:
                            out.append(f"{where}: definedAt {why}")
                    rec = it.get("recipe")
                    if rec is not None and not isinstance(rec, dict):
                        out.append(f"{where}: recipe must be an object")
                    elif isinstance(rec, dict) and rec.get("tokens"):
                        if token_map is None:
                            out.append(f"{where}: recipe names tokens but the kit has no 'tokensFrom'")
                        else:
                            for t in _as_list(rec["tokens"]):
                                if t not in token_map:
                                    out.append(f"{where}: recipe token '{t}' is not in {k['tokensFrom']}")
                else:
                    for f in ("refuses", "why"):
                        if not isinstance(it.get(f), str) or not it[f].strip():
                            out.append(f"{where}: '{f}' is missing")
                    if "instead" not in it:
                        out.append(f"{where}: 'instead' is missing (a piece id, or null with an insteadNote)")
                    elif it["instead"] is None:
                        if not isinstance(it.get("insteadNote"), str) or not it["insteadNote"].strip():
                            out.append(f"{where}: instead is null, so 'insteadNote' must say why there is no piece")
                    elif it["instead"] not in piece_ids:
                        out.append(f"{where}: instead names '{it['instead']}', which is not a piece in any kit")
                    out += _check_detect(where, it)
    return out


def pieces_by_id(craft: dict) -> dict[str, dict]:
    return {p["id"]: p for k in kits(craft) for p in (k.get("pieces") or [])
            if isinstance(p, dict) and isinstance(p.get("id"), str)}


def nogos(craft: dict) -> list[dict]:
    return [n for k in kits(craft) for n in (k.get("noGos") or []) if isinstance(n, dict)]


def _files(paths: Iterable[str]) -> Iterable[Path]:
    for p in paths:
        p = Path(p)
        if p.is_file():
            yield p
        elif p.is_dir():
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
                for fn in sorted(filenames):
                    yield Path(dirpath) / fn


def scan(craft: dict, paths: Iterable[str]) -> list[dict]:
    """Every place in `paths` (files or directories) that a no-go's `detect` pattern matches.

    Each hit: {nogo, file, line, excerpt, instead}. Patterns run over the WHOLE file, so a rule
    spread across lines is caught; write them with [^}]* rather than .* so one match never
    spans two CSS rules."""
    detectors = []
    for n in nogos(craft):
        for d in _as_list(n.get("detect")):
            if isinstance(d, dict) and isinstance(d.get("pattern"), str):
                try:
                    detectors.append((n, re.compile(d["pattern"], re.I), d.get("files") or DEFAULT_FILES))
                except re.error:
                    continue
    if not detectors:
        return []
    hits = []
    for f in _files(paths):
        try:
            if f.stat().st_size > MAX_BYTES:
                continue
        except OSError:
            continue
        mine = [(n, rx) for n, rx, globs in detectors if any(fnmatch.fnmatch(f.name, g) for g in globs)]
        if not mine:
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        for n, rx in mine:
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                start = text.rfind("\n", 0, m.start()) + 1
                excerpt = text[start:start + 200].split("\n")[0].strip()
                hits.append({"nogo": n.get("id"), "file": str(f), "line": line,
                             "excerpt": excerpt, "instead": n.get("instead")})
    return hits


HEX = re.compile(r"(?<![\w&/-])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
# No word boundary in front: a Tailwind arbitrary value glues it on (`shadow-[0_2px_rgba(...)]`).
RGB = re.compile(r"rgba?\(\s*(\d{1,3})\s*[ ,_]\s*(\d{1,3})\s*[ ,_]\s*(\d{1,3})")
# A Tailwind colour utility from Tailwind's own palette (`ring-black/5`, `text-red-500`): a colour
# the universe never chose, written as a class name instead of a literal.
TW = re.compile(r"(?<![\w-])(?:[a-z]+:)*(?:bg|text|border(?:-[trblxy])?|ring|ring-offset|outline|fill|stroke|from|via|to|"
                r"shadow|decoration|divide|accent|caret|placeholder)-(black|(?:slate|gray|zinc|neutral|stone|red|orange|"
                r"amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3})"
                r"(?:/\d{1,3})?(?![\w-])")
ALWAYS = {"#FFFFFF"}


def norm_hex(h: str) -> str:
    """`#abc`, `#abcd`, `#aabbcc` or `#aabbccdd` -> `#AABBCC` (alpha dropped: it is not a colour)."""
    h = h.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    return "#" + h[:6].upper()


BARE_HEX = re.compile(r"^\s*#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\s*$")


def colour_values(node: Any) -> set[str]:
    """Every colour VALUE in a parsed record: a string under a `hex` key, or a string that is
    nothing but a hex. Never a hex quoted inside prose.

    A record's prose names colours in order to REFUSE them ("never the system blue #007AFF")
    or to remember what a token used to be ("tomato #DB371F until 2026-10-12"). Reading every
    hex in the file put those on the palette, so the colour the brand refused passed the gate
    (Continental Works, 2026-10-14)."""
    out: set[str] = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "hex" and isinstance(v, str):
                m = HEX.search(v)
                if m and BARE_HEX.match(v):
                    out.add(norm_hex(m.group(0)))
            else:
                out |= colour_values(v)
    elif isinstance(node, list):
        for v in node:
            out |= colour_values(v)
    elif isinstance(node, str) and BARE_HEX.match(node):
        out.add(norm_hex(node.strip()))
    return out


def palette(root: Path, craft: dict) -> set[str] | None:
    """Every colour the universe declares: each colour VALUE in each kit's `tokensFrom` file
    (its tokens, and whatever the record derives from them as a `hex`), plus white.

    The whole file, not only the `#fragment`: a record declares derived colours beside its
    tokens (the Ascent's `surfaces.frapp.derived`, each with the mix that produces it), and those
    are decisions made in canon. What never counts is a hex written inside a sentence.

    None when no kit names a `tokensFrom`, which means the universe has not said what its colours
    are and there is nothing to hold a surface to."""
    files = {str(k["tokensFrom"]).partition("#")[0] for k in kits(craft) if isinstance(k.get("tokensFrom"), str)}
    if not files:
        return None
    out = set(ALWAYS)
    for f in files:
        try:
            out |= colour_values(json.loads((root / f).read_text(errors="replace")))
        except (OSError, ValueError):
            continue
    return out


def off_palette(allowed: set[str], paths: Iterable[str]) -> list[dict]:
    """Every colour literal in `paths` that `allowed` does not hold: {nogo: 'off-palette', ...}."""
    hits = []
    for f in _files(paths):
        if not any(fnmatch.fnmatch(f.name, g) for g in DEFAULT_FILES):
            continue
        try:
            if f.stat().st_size > MAX_BYTES:
                continue
            lines = f.read_text(errors="replace").split("\n")
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            found = [norm_hex(m.group(0)) for m in HEX.finditer(line)]
            found += ["#%02X%02X%02X" % tuple(min(255, int(x)) for x in m.groups()) for m in RGB.finditer(line)]
            for v in found:
                if v not in allowed:
                    hits.append({"nogo": "off-palette", "file": str(f), "line": i, "value": v,
                                 "excerpt": line.strip()[:200], "instead": None})
            for m in TW.finditer(line):
                hits.append({"nogo": "off-palette", "file": str(f), "line": i, "value": m.group(0),
                             "excerpt": line.strip()[:200], "instead": None})
    return hits


def added_lines(paths: Iterable[str], rng: str) -> set[tuple[str, int]]:
    """(absolute file, line) for every line the git range `rng` adds, in each repo `paths` live in.

    Raises RuntimeError when a path is not in a git repo or git refuses the range, because a gate
    that silently judged nothing would pass everything."""
    import subprocess
    roots = set()
    for p in paths:
        d = Path(p).resolve()
        d = d if d.is_dir() else d.parent
        r = subprocess.run(["git", "-C", str(d), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"{p} is not inside a git repository")
        roots.add(r.stdout.strip())
    out: set[tuple[str, int]] = set()
    for root in roots:
        r = subprocess.run(["git", "-C", root, "diff", "-U0", "--no-color", "--no-ext-diff", rng, "--"],
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"git diff {rng} failed in {root}: {r.stderr.strip()}")
        cur = None
        for line in r.stdout.split("\n"):
            if line.startswith("+++ "):
                cur = None if line[4:] == "/dev/null" else str(Path(root) / line[6:])
            elif line.startswith("@@") and cur:
                m = re.search(r"\+(\d+)(?:,(\d+))?", line)
                start, n = int(m.group(1)), int(m.group(2) or 1)
                out |= {(cur, start + k) for k in range(n)}
    return out


# `abu-allow: <reason>` in any comment syntax. The reason runs to the end of the comment; a closer
# (`*/`, `-->`, `}}`, `*/}`) is not part of it.
WAIVER = re.compile(r"abu-allow:[ \t]*(.*?)[ \t]*(?:\*/\}?|-->|\}\}|$)")
COMMENT_ONLY = re.compile(r"^\s*(?://|/\*|\{/\*|<!--|#|\*|\{\{!--)")


def apply_waivers(hits: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split hits into (refused, waived). A line is waived by `abu-allow: <reason>` on that line or
    the line directly above it, and only with a reason: a skip nobody can explain is how drift
    comes back. A bare `abu-allow:` waives nothing and marks the hit `bareWaiver` so the output can
    say why it still failed. Earned 2026-10-14: an iMessage simulator must keep the real iOS blue
    the brand refuses as a brand colour, and a baseline cannot excuse code written after it."""
    cache: dict[str, list[str]] = {}
    refused, waived = [], []
    for h in hits:
        lines = cache.get(h["file"])
        if lines is None:
            try:
                lines = Path(h["file"]).read_text(errors="replace").split("\n")
            except OSError:
                lines = []
            cache[h["file"]] = lines
        reason, bare = None, False
        for n in (h["line"], h["line"] - 1):
            if 1 <= n <= len(lines):
                text = lines[n - 1]
                # The line above counts only when it is a comment by itself: a waiver at the end of
                # a line of code excuses that line, never the one under it.
                if n != h["line"] and not COMMENT_ONLY.match(text):
                    continue
                m = WAIVER.search(text)
                if m:
                    if m.group(1).strip():
                        reason = m.group(1).strip()
                        break
                    bare = True
        if reason:
            waived.append(dict(h, waiver=reason))
        else:
            refused.append(dict(h, bareWaiver=True) if bare else h)
    return refused, waived


def only_added(hits: list[dict], added: set[tuple[str, int]]) -> list[dict]:
    return [h for h in hits if (str(Path(h["file"]).resolve()), h["line"]) in added]


def _key(h: dict, base: Path) -> tuple:
    """What a finding IS, independent of where it currently sits: line numbers move, so a baseline
    keys on the file, the rule, the value and the line's text."""
    try:
        f = str(Path(h["file"]).resolve().relative_to(base.resolve()))
    except ValueError:
        f = str(h["file"])
    return (f, h.get("nogo") or "", h.get("value") or "", re.sub(r"\s+", " ", h.get("excerpt") or "").strip())


def write_baseline(hits: list[dict], path: str, base: Path) -> int:
    rows = sorted(_key(h, base) for h in hits)
    Path(path).write_text(json.dumps({"version": 1, "note": "Findings this surface carried when the gate was switched on. "
                                      "check-kit --baseline tolerates these and refuses anything new; fix one and delete its row.",
                                      "findings": [dict(zip(("file", "nogo", "value", "excerpt"), r)) for r in rows]}, indent=1) + "\n")
    return len(rows)


def beyond_baseline(hits: list[dict], path: str, base: Path) -> list[dict]:
    """The hits a committed baseline does not account for, counting duplicates (two identical lines
    are two findings, so fixing one never silently excuses a new one)."""
    from collections import Counter
    data = json.loads(Path(path).read_text())
    left = Counter(tuple(r.get(k, "") for k in ("file", "nogo", "value", "excerpt")) for r in data.get("findings", []))
    out = []
    for h in hits:
        k = _key(h, base)
        if left[k] > 0:
            left[k] -= 1
        else:
            out.append(h)
    return out

