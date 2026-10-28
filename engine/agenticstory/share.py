"""`abu check-share`: every page a site ships unfurls as ITSELF.

Gary, 2026-10-16: "Update the guard to worry more than tech specs", then "put this at the most general
level possible because people are always making websites if they're having an agentic brand universe".
Earned on continentalworks.ai/supersuit/computer, which shipped wearing /supersuit's share card (a
plinth and "By introduction only") while every unfurl check passed: those measure the card (1200x630,
absolute, 200, under 1MB) and none asks whether it is THIS page's card. A link to "what computer to
get" that unfurls as "by introduction only" is broken however correct its bytes are.

So it needs no universe: it is a check on any site. A page must name a share card no other page names,
or carry its own card file. A page that names none unfurls as the site default, which is the same
failure one step removed. It reads two shapes:

  Next.js App Router  app/**/page.*, its metadata in the page or a sibling layout.*, a card named as
                      `shareCards.<key>` or a literal "/og/....png|jpg" path; an opengraph-image or
                      twitter-image file in the page's folder is its own card.
  Plain HTML          *.html, its card the og:image (or twitter:image) meta.

With `added`, only pages the git range ADDS are judged, so a site carrying old shared cards can still
ship a new page cleanly; without it, every page is. `Share-Waiver: <why>` in a commit in the range lets a
deliberate exception through, on the record. What it cannot judge is whether the card DEPICTS the page:
that stays a look.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

SKIP_DIRS = {"node_modules", ".git", ".next", "dist", "build", "out", ".docusaurus", ".vercel", "vendor", "coverage"}
NEXT_PAGE = re.compile(r"(^|/)app/(.+/)?page\.(tsx|jsx|ts|js|mdx)$")
HTML_PAGE = re.compile(r"\.html?$")
CARD_FILE = re.compile(r"^(opengraph-image|twitter-image)\.(tsx|jsx|ts|js|png|jpe?g)$")
LAYOUT = re.compile(r"^layout\.(tsx|jsx|ts|js)$")
KEY = re.compile(r"shareCards\.(\w+)")
LITERAL = re.compile(r"""["'`](/og/[^"'`\s]+\.(?:png|jpe?g))["'`]""")
# A meta-refresh redirect (a renamed page's forwarding stub) is not a page anyone shares: its link
# lands on the target, which unfurls as itself (supersuit-wiki#17, 2026-10-28: a skill rename's
# generated redirect needed a Share-Waiver to push).
REDIRECT = re.compile(r"""<meta[^>]+http-equiv=["']refresh["'][^>]*content=["'][^"']*url=""", re.I)
META = re.compile(r"""<meta[^>]+(?:property|name)=["'](?:og:image|twitter:image)["'][^>]*content=["']([^"']+)["']""", re.I)


def cards_named(text: str) -> set[str]:
    """The share cards a source file names: `shareCards.<key>` references and literal /og/ paths."""
    return {f"shareCards.{m}" for m in KEY.findall(text)} | set(LITERAL.findall(text))


def _skipped(rel: str) -> bool:
    return any(part in SKIP_DIRS for part in Path(rel).parts)


def is_page(rel: str) -> bool:
    return not _skipped(rel) and bool(NEXT_PAGE.search(rel) or HTML_PAGE.search(rel))


def _read(p: Path) -> str:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return ""


def page_cards(root: Path, rel: str) -> set[str] | None:
    """The cards a page names, or None when there is nothing to compare: it carries its own card
    file, or it is a redirect whose link lands on (and unfurls as) its target."""
    p = root / rel
    if HTML_PAGE.search(rel):
        text = _read(p)
        if REDIRECT.search(text):
            return None
        return {re.sub(r"^https?://[^/]+", "", m) for m in META.findall(text)}
    folder = p.parent
    if any(CARD_FILE.match(f.name) for f in folder.iterdir()):
        return None
    text = _read(p) + "\n".join(_read(f) for f in folder.iterdir() if LAYOUT.match(f.name))
    return cards_named(text)


def all_pages(root: Path) -> list[str]:
    out = []
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and is_page(rel):
            out.append(rel)
    return sorted(out)


def _git(root: Path, *a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True)


def added_pages(root: Path, rng: str) -> list[str]:
    """Pages the range adds. Raises RuntimeError when git refuses, because a gate that judged
    nothing would pass everything."""
    r = _git(root, "diff", "--name-only", "--diff-filter=A", rng, "--")
    if r.returncode:
        raise RuntimeError(f"git could not read the range {rng}: {r.stderr.strip()}")
    return [f for f in r.stdout.splitlines() if f and is_page(f) and (root / f).exists()]


def waiver(root: Path, rng: str) -> str | None:
    if ".." not in rng:
        return None
    m = re.search(r"^Share-Waiver:\s*(\S.*)$", _git(root, "log", "--format=%B", rng).stdout, re.M)
    return m.group(1).strip() if m else None


def check_share(root, added: str | None = None) -> tuple[list[dict], str | None]:
    """(findings, waiver). A finding is {page, problem: "no-card" | "shared", card?, sharedWith?}.
    With a waiver in the range the findings are cleared and the waiver's reason returned."""
    root = Path(root).resolve()
    pages = all_pages(root)
    judged = added_pages(root, added) if added else pages
    named = {p: page_cards(root, p) for p in pages}
    for p in judged:
        named.setdefault(p, page_cards(root, p))
    hits: list[dict] = []
    for page in judged:
        cards = named[page]
        if cards is None:
            continue
        if not cards:
            hits.append({"page": page, "problem": "no-card"})
            continue
        for card in sorted(cards):
            other = next((o for o in pages if o != page and named.get(o) and card in named[o]), None)
            if other:
                hits.append({"page": page, "problem": "shared", "card": card, "sharedWith": other})
    if hits and added:
        why = waiver(root, added)
        if why:
            return [], why
    return hits, None


def describe(h: dict) -> str:
    if h["problem"] == "no-card":
        return f"{h['page']}  NO CARD  -> it names no share card, so its link unfurls as the site's default"
    return f"{h['page']}  SHARED CARD {h['card']}  -> that is {h['sharedWith']}'s card, so its link unfurls as that page"
