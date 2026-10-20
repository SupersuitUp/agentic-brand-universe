"""A brand "direction": the small JSON an exploration settles on, before it becomes a universe.

Shape (see `abu seed`): name, concept, palette{ground,ink,accent[,lightGround,lightInk]},
type{display,body}, mark{kind: monogram|svg, ...}, sources[].
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
REQUIRED_COLORS = ("ground", "ink", "accent")
OPTIONAL_COLORS = ("lightGround", "lightInk", "lightAccent")


def load_direction(path) -> dict:
    return json.loads(Path(path).read_text())


def validate_direction(d) -> list[str]:
    """Every defect, naming the field. Empty when the direction is sound."""
    errs: list[str] = []
    if not isinstance(d, dict):
        return ["direction must be an object"]
    if not isinstance(d.get("name"), str) or not d["name"].strip():
        errs.append("name: required non-empty string")
    pal = d.get("palette")
    if not isinstance(pal, dict):
        errs.append("palette: required object")
        pal = {}
    for k in REQUIRED_COLORS:
        if k not in pal:
            errs.append(f"palette.{k}: required")
    for k in REQUIRED_COLORS + OPTIONAL_COLORS:
        if k in pal and not (isinstance(pal[k], str) and HEX.match(pal[k])):
            errs.append(f"palette.{k}: not a hex color: {pal[k]!r}")
    typ = d.get("type")
    if not isinstance(typ, dict):
        errs.append("type: required object")
        typ = {}
    for k in ("display", "body"):
        if not isinstance(typ.get(k), str) or not typ[k].strip():
            errs.append(f"type.{k}: required non-empty font family")
    mark = d.get("mark")
    if not isinstance(mark, dict):
        errs.append("mark: required object")
    else:
        kind = mark.get("kind")
        if kind == "monogram":
            if not isinstance(mark.get("letters"), str) or not mark["letters"].strip():
                errs.append("mark.letters: required for a monogram")
        elif kind == "svg":
            if not isinstance(mark.get("svg"), str) or "<svg" not in mark["svg"]:
                errs.append("mark.svg: required SVG text for kind svg")
        else:
            errs.append(f"mark.kind: must be monogram or svg, got {kind!r}")
    return errs
