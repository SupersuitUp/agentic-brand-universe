"""lifecycle.py: the ONE check every drawing verb runs before it casts an entity (SPEC §4.15.2).

An archived entity (`lifecycle: "archived"`, SPEC v0.19) must not be drawn into a NEW work.
Until 1.50.0 only compose-spread enforced that, inline. `on-brand-image --entity` and
`compose-strip` did not look at lifecycle at all, so a retired design came straight back
through a strip or a one-off hero. Earned 2026-11-23: continental-works archived
freedom-character (Gary Sheng: "Most important thing to retire is the heavenly orb with halo I
think"), and its wiki-hero form would still have drawn her, because the strip route never asked.

Every verb now calls `archived_notes` here and refuses on a non-empty answer, so the wording, the
replacement hint and the rule are one implementation, not three copies that drift. The override
(`allowArchived` on a spread or a strip panel, `--allow-archived` on generate.py) is per call
and recorded, because re-rendering something that shipped before the archive is legitimate and
must leave a trace.
"""
from __future__ import annotations

from typing import Iterable, Mapping


def is_archived(raw: Mapping | None) -> bool:
    return bool(raw) and raw.get("lifecycle") == "archived"


def archive_note(eid: str, raw: Mapping) -> str:
    """One line an author can act on: why it was retired and what to cast instead."""
    a = raw.get("archived") or {}
    bits = [f"'{eid}' is ARCHIVED"]
    if a.get("on"):
        bits.append(f"on {a['on']}")
    if a.get("reason"):
        bits.append(f"({a['reason']})")
    if a.get("supersededBy"):
        bits.append(f"-> cast '{a['supersededBy']}' instead")
    return " ".join(bits)


def archived_notes(cast: Iterable[tuple[str, Mapping | None]]) -> list[str]:
    """Given (entity id, raw entity dict) pairs, the note for each archived one, in order."""
    return [archive_note(eid, raw) for eid, raw in cast if is_archived(raw)]


def refusal(where: str, notes: list[str], override: str) -> str:
    """The refusal text every verb prints. `override` names that verb's own escape hatch."""
    return (f"ARCHIVED ENTITY CAST ({where}): " + "; ".join(notes)
            + f". Cast the replacement, or {override} if you are deliberately re-rendering "
              "a work that shipped before the archive.")
