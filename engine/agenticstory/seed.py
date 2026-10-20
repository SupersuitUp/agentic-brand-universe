"""`abu seed`: write a freshly-scaffolded universe's brand from a direction.

Writes the palette, type, mark and brief into canon, and declares `identity.surfaces` so
freedom-brand.mjs (`emit --surface artifact`) reads the colors. Every file gets a
`.recipe.json` sibling (generator `abu seed`) so provenance is never missing.
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.dom.minidom as minidom
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from .direction import validate_direction


def fonts_url(display: str, body: str) -> str:
    return ("https://fonts.googleapis.com/css2?family=" + quote_plus(display) + ":wght@400;600"
            "&family=" + quote_plus(body) + ":wght@400;500;600&display=swap")


_OWN_BG = re.compile(r"<svg[^>]*>\s*<rect[^>]*width=[\"'](?:100%|\d+(?:\.\d+)?)[\"'][^>]*height=[\"'](?:100%|\d+(?:\.\d+)?)[\"']", re.I)
_VIEWBOX = re.compile(r"viewBox=[\"']([^\"']+)[\"']")


def favicon_svg(mark_svg: str, accent: str) -> str:
    """A square tab icon from the mark. A mark that already opens with a full-size background rect
    is used as it is; any other mark is nested, inset, on an accent tile with a square viewBox."""
    if _OWN_BG.search(mark_svg):
        return mark_svg
    vb = _VIEWBOX.search(mark_svg)
    box = vb.group(1) if vb else "0 0 100 100"
    inner = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", mark_svg)
    def root(m):  # drop the root's own size, position and namespace; the tile supplies them
        attrs = re.sub(r'\s(?:xmlns|width|height|x|y|viewBox)=("[^"]*"|\'[^\']*\')', "", m.group(1))
        return f'<svg x="14" y="14" width="72" height="72" viewBox="{box}"{attrs}>'
    inner = re.sub(r"<svg\b([^>]*)>", root, inner, count=1)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">'
            f'<rect width="100" height="100" rx="14" fill="{accent}"/>{inner.strip()}</svg>\n')


_DROP = {"script", "foreignobject"}


def sanitize_svg(svg: str) -> str:
    """Parse the mark as XML and return it without script, foreignObject, on* handlers or javascript: links.
    Raises ValueError when it is not a well-formed SVG document."""
    try:
        doc = minidom.parseString(svg.encode() if isinstance(svg, str) else svg)
    except Exception as e:  # noqa: BLE001 - any parse failure is "not an SVG"
        raise ValueError(f"mark is not well-formed SVG ({e})") from None
    root = doc.documentElement
    if root.localName != "svg":
        raise ValueError(f"mark is not an SVG document (root is <{root.localName}>)")

    def walk(node):
        for child in list(node.childNodes):
            if child.nodeType != child.ELEMENT_NODE:
                continue
            if (child.localName or child.tagName).lower() in _DROP:
                node.removeChild(child)
                continue
            walk(child)
        if node.nodeType == node.ELEMENT_NODE:
            for name in list(node.attributes.keys()):
                val = node.getAttribute(name)
                if name.lower().startswith("on") or val.strip().lower().startswith("javascript:"):
                    node.removeAttribute(name)
    walk(root)
    return root.toxml() + "\n"


def seed_universe(root, direction: dict, *, brief_md: str, board_png=None, mark_svg: str) -> list[str]:
    errs = validate_direction(direction)
    if errs:
        raise ValueError("invalid direction: " + "; ".join(errs))
    # Validate every input BEFORE writing anything, so a bad one leaves the universe untouched.
    if not isinstance(brief_md, str) or not brief_md.strip():
        raise ValueError("brief is empty")
    mark_svg = sanitize_svg(mark_svg)
    if board_png is not None:
        bp = Path(board_png)
        if not bp.is_file():
            raise ValueError(f"board {bp} does not exist")
        if not bp.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError(f"board {bp} is not a PNG")
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
    tokens = {k: pal[k] for k in ("ground", "ink", "accent", "lightGround", "lightInk", "lightAccent") if k in pal}
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
    write("marks/favicon.svg", favicon_svg(mark_svg, pal["accent"]))
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
            "roles": {"ground": "lightGround", "text": "lightInk",
                      "accent": "lightAccent" if "lightAccent" in pal else "accent"},
            "display": typ["display"]}
    ident["surfaces"] = surfaces
    ident["mark"] = "marks/mark.svg"
    ident["favicon"] = "marks/favicon.svg"
    ident["theme"] = direction["name"]
    if board_png is not None:
        ident.setdefault("register", {})["anchor"] = "reference/register/board.png"
    manifest.write_text(json.dumps(u, indent=2) + "\n")
    written.append(str(manifest))
    return written
