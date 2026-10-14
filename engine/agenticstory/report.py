"""Filing what ABU got wrong, with the context a maintainer needs to act on it.

Nothing here sends anything. `issue_url` builds a GitHub new-issue page, pre-filled; the person
reads it and presses submit. That keeps the reporter in charge of what leaves their machine,
which matters because a finding's excerpt is a line of THEIR code.

Earned 2026-10-14. Gary: "it should be easy to suggest changes for anything that we ship to
people", and "it is very very important that really good context gets put into the issues so
that we can address them really well". So every body carries the same skeleton (what happened,
what was expected, the command, the environment), and check-kit fills it with the findings and
the rule each one broke, including who decided the rule and in what words.
"""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from urllib.parse import urlencode

REPO = "SupersuitUp/agentic-brand-universe"
# GitHub serves a new-issue URL up to about 8 KB; past that it errors instead of opening the form.
MAX_URL = 7800
TRIMMED = "\n\n_(Trimmed to fit a GitHub link. Run the command above to see the rest.)_"


def abu_version() -> str:
    """The released version. The package `__version__` is a placeholder; the release is what the
    plugin manifest (repo checkout) or package.json (npm install) declares."""
    root = Path(__file__).resolve().parents[2]
    for rel in (".claude-plugin/plugin.json", "package.json"):
        p = root / rel
        try:
            v = json.loads(p.read_text()).get("version")
        except (OSError, ValueError):
            continue
        if isinstance(v, str) and v:
            return v
    from . import __version__
    return __version__


def environment() -> dict:
    return {"abu": abu_version(), "python": platform.python_version(),
            "os": f"{platform.system()} {platform.release()} ({platform.machine()})"}


def body(what: str, expected: str = "", command: str = "", skill: str = "", details: str = "") -> str:
    env = environment()
    parts = [
        "## What happened", what.strip() or "_(describe what ABU did)_",
        "## What I expected", expected.strip() or "_(what should it have done, and why? This is the part we need most.)_",
        "## Steps or command", f"```\n{command.strip()}\n```" if command.strip() else "_(the command you ran, or what you asked the agent)_",
    ]
    if skill.strip():
        parts += ["## Skill", skill.strip()]
    if details.strip():
        parts += ["## Details", details.strip()]
    parts += ["## Environment",
              f"- ABU version: {env['abu']}\n- Python: {env['python']}\n- OS: {env['os']}"]
    return "\n\n".join(parts)


def issue_url(title: str, text: str, repo: str = REPO) -> str:
    def build(t):
        return f"https://github.com/{repo}/issues/new?" + urlencode({"title": title[:200], "body": t})
    url = build(text)
    if len(url) <= MAX_URL:
        return url
    lo, hi = 0, len(text)
    while lo < hi:  # the longest prefix that still fits once the trim note is added
        mid = (lo + hi + 1) // 2
        if len(build(text[:mid] + TRIMMED)) <= MAX_URL:
            lo = mid
        else:
            hi = mid - 1
    return build(text[:lo] + TRIMMED)


def check_kit_details(hits: list[dict], nogos: dict, pieces: dict, limit: int = 12) -> str:
    """Each finding with the rule it broke: the rule's own words, why, who decided it and how."""
    out = []
    for h in hits[:limit]:
        where = f"`{h['file']}:{h['line']}`"
        if h["nogo"] == "off-palette":
            head = f"- {where} OFF-PALETTE {h.get('value')}: a colour the kit's tokensFrom does not hold"
        else:
            n = nogos.get(h["nogo"]) or {}
            inst = (pieces.get(h.get("instead") or "") or {}).get("name") or h.get("instead") or n.get("insteadNote") or "-"
            d = n.get("decided") or {}
            ruling = ", ".join(x for x in (d.get("by"), d.get("on")) if x)
            said = f' ("{d["verbatim"]}")' if d.get("verbatim") else ""
            head = (f"- {where} NO-GO `{h['nogo']}`: refuses {n.get('refuses', '?')}; why: {n.get('why', '?')}; "
                    f"instead: {inst}; decided: {ruling or '?'}{said}")
        out.append(f"{head}\n  ```\n  {h.get('excerpt', '')}\n  ```")
    if len(hits) > limit:
        out.append(f"- and {len(hits) - limit} more finding(s)")
    return "\n".join(out)
