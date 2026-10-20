"""`abu seed`: write a freshly-scaffolded universe's brand from a direction.

Writes the palette, type, mark and brief into canon, and declares `identity.surfaces` so
freedom-brand.mjs (`emit --surface artifact`) reads the colors. Every file gets a
`.recipe.json` sibling (generator `abu seed`) so provenance is never missing.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from .direction import validate_direction


def fonts_url(display: str, body: str) -> str:
    return ("https://fonts.googleapis.com/css2?family=" + quote_plus(display) + ":wght@400;600"
            "&family=" + quote_plus(body) + ":wght@400;500;600&display=swap")


def seed_universe(root, direction: dict, *, brief_md: str, board_png=None, mark_svg: str) -> list[str]:
    errs = validate_direction(direction)
    if errs:
        raise ValueError("invalid direction: " + "; ".join(errs))
    root = Path(root).resolve()
    manifest = root / "universe.json"
    if not manifest.exists():
        raise FileNotFoundError(f"{manifest} not found (run `abu init` first)")
    written: list[str] = []
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def write(rel: str, content: str | bytes, inputs=()) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode() if isinstance(content, str) else content
        p.write_bytes(data)
        written.append(str(p))
        recipe = {"generator": "abu seed", "createdAt": stamp, "direction": direction["name"],
                  "inputs": list(inputs), "sha256": hashlib.sha256(data).hexdigest()}
        r = p.with_name(p.name + ".recipe.json")
        r.write_text(json.dumps(recipe, indent=2, sort_keys=True) + "\n")
        written.append(str(r))

    pal, typ = direction["palette"], direction["type"]
    tokens = {k: pal[k] for k in ("ground", "ink", "accent", "lightGround", "lightInk") if k in pal}
    write("canon/craft/palette.json", json.dumps({
        "id": "palette", "kind": "register-rule",
        "summary": f"{direction['name']} palette: ground, ink and accent tokens a surface reads by role.",
        "tokens": tokens}, indent=2) + "\n")
    write("canon/craft/type.json", json.dumps({
        "id": "type", "kind": "register-rule",
        "summary": f"{direction['name']} type: display and body families.",
        "display": typ["display"], "body": typ["body"],
        "fontsUrl": fonts_url(typ["display"], typ["body"])}, indent=2) + "\n")
    write("marks/mark.svg", mark_svg)
    write("canon/craft/brand-brief.md", brief_md)
    if board_png is not None:
        write("reference/register/board.png", Path(board_png).read_bytes(),
              inputs=[str(board_png)])

    u = json.loads(manifest.read_text())
    ident = u.setdefault("identity", {})
    dark = {"tokens": "canon/craft/palette.json#tokens",
            "roles": {"ground": "ground", "text": "ink", "accent": "accent"},
            "display": typ["display"]}
    surfaces = {"default": dark, "artifact": dict(dark)}
    if "lightGround" in pal and "lightInk" in pal:
        surfaces["artifact-light"] = {
            "tokens": "canon/craft/palette.json#tokens",
            "roles": {"ground": "lightGround", "text": "lightInk", "accent": "accent"},
            "display": typ["display"]}
    ident["surfaces"] = surfaces
    ident["mark"] = "marks/mark.svg"
    ident["theme"] = direction["name"]
    if board_png is not None:
        ident.setdefault("register", {})["anchor"] = "reference/register/board.png"
    manifest.write_text(json.dumps(u, indent=2) + "\n")
    written.append(str(manifest))
    return written
