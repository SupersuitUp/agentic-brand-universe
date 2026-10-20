#!/usr/bin/env python3
"""Outline some letters of a Google Fonts family as one SVG path, fitted to a 100x100 box.

Usage: glyph-paths.py <family> <letters> [--weight 600] [--tracking -0.03]
Prints JSON: {"d": "<path data>", "family": ..., "letters": ...}.
Fetches the family's subset (css2 `text=` parameter) from Google Fonts with an old UA so the
reply is a single static font file, then reads the outlines with fontTools. Needs fontTools
and brotli: mark.mjs runs this under `uv run --with fonttools==<pin> --with brotli==<pin>`, so nothing is
installed into any Python.
"""
import argparse, json, re, sys, tempfile, urllib.error, urllib.parse, urllib.request

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0 Safari/537.36"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def css_for(family, weight, text):
    """The css2 reply for the family. A single-weight family (Bebas Neue, Abril Fatface) answers 400
    to a weight axis, so retry without it and take the weight it has."""
    def url(axis):
        fam = f"{family}:wght@{weight}" if axis else family
        return "https://fonts.googleapis.com/css2?" + urllib.parse.urlencode({"family": fam, "text": text})
    try:
        return fetch(url(True)).decode()
    except urllib.error.HTTPError as e:
        if e.code != 400:
            sys.exit(f"glyph-paths: could not get {family!r} from Google Fonts ({e}); it may not be a Google font")
    try:
        return fetch(url(False)).decode()
    except Exception as e:
        sys.exit(f"glyph-paths: could not get {family!r} from Google Fonts ({e}); it may not be a Google font")


def load_font(family, weight, text):
    css = css_for(family, weight, text)
    m = re.search(r"url\(([^)]+)\)", css)
    if not m:
        sys.exit(f"glyph-paths: no font file in the Google Fonts reply for {family!r}")
    with tempfile.TemporaryDirectory() as d:  # removes both temp files, even on error
        src, dst = d + "/in.font", d + "/static.font"
        open(src, "wb").write(fetch(m.group(1)))
        font = TTFont(src)
        if "fvar" in font:
            from fontTools.varLib import instancer
            ax = next((a for a in font["fvar"].axes if a.axisTag == "wght"), None)
            if ax is not None:  # the nearest weight the font has
                font = instancer.instantiateVariableFont(font, {"wght": max(ax.minValue, min(ax.maxValue, weight))})
        font.save(dst)
        return TTFont(dst, lazy=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("family"); ap.add_argument("letters")
    ap.add_argument("--weight", type=int, default=600)
    ap.add_argument("--tracking", type=float, default=0.0, help="em units added between letters")
    a = ap.parse_args()
    letters = a.letters.upper()
    font = load_font(a.family, a.weight, letters)
    gs, cmap, upm = font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm
    names = []
    for ch in letters:
        if ord(ch) not in cmap:
            sys.exit(f"glyph-paths: {a.family!r} has no glyph for {ch!r}")
        names.append(cmap[ord(ch)])
    # lay out in font units (y up), measure, then fit and flip into a 100x100 box
    offsets, x = [], 0
    for n in names:
        offsets.append(x); x += gs[n].width + a.tracking * upm
    bp = BoundsPen(gs)
    for n, off in zip(names, offsets):
        gs[n].draw(TransformPen(bp, (1, 0, 0, 1, off, 0)))
    x0, y0, x1, y1 = bp.bounds
    bw, bh = x1 - x0, y1 - y0
    s = min(60 / bw, 56 / bh)
    tx, ty = 50 - (x0 + bw / 2) * s, 50 + (y0 + bh / 2) * s
    pen = SVGPathPen(gs, ntos=lambda v: ("%.2f" % v).rstrip("0").rstrip("."))
    for n, off in zip(names, offsets):
        gs[n].draw(TransformPen(pen, (s, 0, 0, -s, tx + off * s, ty)))
    print(json.dumps({"d": pen.getCommands(), "family": a.family, "letters": letters}))


if __name__ == "__main__":
    main()
