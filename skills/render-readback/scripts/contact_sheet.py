#!/usr/bin/env python3
# /// script
# dependencies = ["pillow"]
# ///
# ^ PEP 723 inline metadata, so `uv run <this script>` resolves Pillow itself.
#   Before this, every invocation needed `uv run --with pillow` typed from memory,
#   and the takeoff-thursdays run (2026-08) paid that tax on every single readback.
"""Build a labelled contact sheet from renders, for read-back.

`render-readback` says a contact sheet of four is the right read-back unit, because it
catches composition, wrong character, invented people, panels, photoreal drift and gross
canon breaches in one look. It shipped no tool, so every run hand-rolled the same PIL
montage. Ten times in one session (nation-of-fire, 2026-07-30) before this was promoted.

  python3 contact_sheet.py --out sheet.png a.png b.png c.png d.png
  python3 contact_sheet.py --out sheet.png --cols 3 --width 700 spreads/*.png
  python3 contact_sheet.py --out sheet.png --cover reference/jerry a.png b.png

A PARTIAL SHEET IS A LIE, AND `--cover` IS THE HALF THAT WAS MISSING (SPEC v0.49).
`shoot-references` tells its reader that this script "already refuses a partial one, so a
short sheet cannot read as 'everything I rendered'". That was only ever true of a file
that does not exist. Nothing here knew what the BATCH was, so a sheet built from three of
twelve renders was built happily and read, to the operator looking at it, as twelve. That
is the exact failure the refusal below was described as preventing, and the SHOW THE
OPERATOR EVERY SHOT gate is the rule it was protecting.

`--cover DIR` names the batch: every `*.png` in DIR that is not itself a sheet or a
parked candidate must appear on the sheet, or this REFUSES and names what is missing.

AT THE SIZE AND ON THE GROUND IT WILL LIVE ON (issue #59, SPEC v0.62).

  python3 contact_sheet.py --out at-size.png --at-size 64,240 --background '#FBF5E7' *.png

An avatar shown at 64 px on paper cannot be judged from a 690 px cell on white: detail that
reads beautifully large turns to mud small, and a ground colour changes every edge. Reader
portraits on 2026-10-15 needed exactly that view and a one-off script drew it. `--at-size`
draws one band per size, each image with its LONGEST edge at exactly that many pixels (aspect
kept, never cropped), labelled under the image. `--background` is the surface's ground, used
for the whole sheet and composited under any transparency; without `--at-size` it recolours
the ordinary sheet's ground and letterbox instead.
"""
import argparse, os, re, sys

def _colour(v):
    """`#RRGGBB` (or `RRGGBB`, `#RGB`) to an RGB tuple, or None."""
    m = re.fullmatch(r"#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})", (v or "").strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _sizes(v):
    """`64,240` (repeatable) to [64, 240], or None if any entry is not a positive int."""
    out = []
    for chunk in v:
        for part in str(chunk).split(","):
            part = part.strip()
            if not part.isdigit() or int(part) <= 0 or int(part) > 4096:
                return None
            out.append(int(part))
    return out

def _ink(ground):
    """Label ink that reads on the ground: dark on a light ground, light on a dark one."""
    lum = 0.2126 * ground[0] + 0.7152 * ground[1] + 0.0722 * ground[2]
    return (30, 27, 25) if lum > 140 else (246, 240, 228)

def _font(px):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=px)
    except TypeError:  # Pillow < 10.1 has one bitmap size
        return ImageFont.load_default()

def _open(path, ground):
    """The image upright (EXIF honoured) and flattened onto the ground, never onto black."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(path))
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        base = Image.new("RGBA", im.size, ground + (255,))
        base.alpha_composite(im)
        return base.convert("RGB")
    return im.convert("RGB")

def at_size_sheet(paths, sizes, ground, cols, label):
    """One band per size: a header, then every image with its longest edge == size."""
    from PIL import Image, ImageDraw
    ink, pad = _ink(ground), 32
    head_f, lab_f = _font(18), _font(13)
    head_h, lab_h = 30, (20 if label else 0)
    cols = max(1, min(cols, len(paths)))
    rows = (len(paths) + cols - 1) // cols
    names = [os.path.basename(p) for p in paths]
    bands = []
    for s in sizes:
        # A cell is at least the size, and wide enough for its label at small sizes.
        cell_w = max(s, max((len(n) for n in names), default=0) * 7 if label else 0)
        bands.append((s, cell_w, head_h + rows * (s + lab_h + pad)))
    width = pad + max(cols * (cw + pad) for _, cw, _ in bands)
    height = pad + sum(h for _, _, h in bands)
    sheet = Image.new("RGB", (width, height), ground)
    draw = ImageDraw.Draw(sheet)
    imgs = [_open(p, ground) for p in paths]
    y = pad
    for s, cell_w, band_h in bands:
        draw.text((pad, y), f"at {s} px", fill=ink, font=head_f)
        top = y + head_h
        for i, im in enumerate(imgs):
            k = s / max(im.size)
            fit = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))),
                            Image.LANCZOS)
            cx = pad + (i % cols) * (cell_w + pad)
            cy = top + (i // cols) * (s + lab_h + pad)
            sheet.paste(fit, (cx + (cell_w - fit.size[0]) // 2, cy + (s - fit.size[1]) // 2))
            if label:
                draw.text((cx, cy + s + 4), names[i], fill=ink, font=lab_f)
        y += band_h
    return sheet

# A sheet is not one of its own inputs, and neither is a parked roll: `candidates/` is
# history, by the make-a-book rule that every roll the operator has seen is copied there
# before the next one overwrites it.
_NOT_A_SHOT = ("contact-sheet", "contact_sheet", "sheet", "crop", "zoom", "montage")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=None,
                    help="columns (default 2; with --at-size, every image in one row up to 6)")
    ap.add_argument("--width", type=int, default=690, help="per-cell width in px")
    ap.add_argument("--label", action="store_true", default=True)
    ap.add_argument("--no-label", dest="label", action="store_false")
    ap.add_argument("--cover", metavar="DIR", default=None,
                    help="the batch this sheet must cover: refuse unless every shot in "
                         "DIR is on it, so a short sheet cannot read as everything")
    ap.add_argument("--at-size", action="append", default=[], metavar="PX[,PX]",
                    help="draw each image with its longest edge at exactly PX, one band per "
                         "size, e.g. 64,240: judge a set at the size the surface shows it")
    ap.add_argument("--background", default=None, metavar="#RRGGBB",
                    help="the surface's ground colour, for the sheet and under transparency")
    a = ap.parse_args()
    ground = (255, 255, 255)
    if a.background is not None:
        ground = _colour(a.background)
        if ground is None:
            sys.stderr.write(f"contact_sheet: --background {a.background!r} is not a hex "
                             "colour like '#FBF5E7'\n")
            return 2
    sizes = _sizes(a.at_size) if a.at_size else []
    if sizes is None:
        sys.stderr.write(f"contact_sheet: --at-size {','.join(a.at_size)!r} must be positive "
                         "pixel sizes, e.g. 64,240\n")
        return 2
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return int(bool(sys.stderr.write(
            "contact_sheet: needs pillow. Run via `uv run <this script>` (it declares "
            "pillow inline, PEP 723) or install Pillow in this env.\n")))

    paths = [p for p in a.images if os.path.exists(p)]
    missing = [p for p in a.images if not os.path.exists(p)]
    if missing:
        # Fail loudly: a silently short contact sheet reads as "everything I rendered",
        # which is exactly how a missing spread goes unnoticed.
        sys.stderr.write("contact_sheet: MISSING, refusing to build a partial sheet:\n")
        for m in missing:
            sys.stderr.write(f"  {m}\n")
        return 1
    if not paths:
        sys.stderr.write("contact_sheet: no images\n")
        return 1

    if a.cover:
        if not os.path.isdir(a.cover):
            sys.stderr.write(f"contact_sheet: --cover {a.cover} is not a directory\n")
            return 1
        on_sheet = {os.path.realpath(p) for p in paths}
        want = []
        for name in sorted(os.listdir(a.cover)):
            if not name.lower().endswith(".png"):
                continue
            if any(tell in name.lower() for tell in _NOT_A_SHOT):
                continue
            full = os.path.join(a.cover, name)
            if os.path.realpath(full) == os.path.realpath(a.out):
                continue
            want.append(full)
        absent = [p for p in want if os.path.realpath(p) not in on_sheet]
        if absent:
            sys.stderr.write(
                f"contact_sheet: REFUSING a partial sheet. {len(absent)} of "
                f"{len(want)} shot(s) in {a.cover} are not on it:\n")
            for p in absent:
                sys.stderr.write(f"  {p}\n")
            sys.stderr.write(
                "  A short sheet reads to whoever looks at it as everything that was\n"
                "  rendered, which is how a shot reaches nobody while the step reports\n"
                "  success. Add them, or point --cover at the batch you actually mean.\n")
            return 1

    if sizes:
        sheet = at_size_sheet(paths, sizes, ground, a.cols or min(len(paths), 6), a.label)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        sheet.save(a.out)
        print(f"[contact-sheet] {len(paths)} image(s) at {', '.join(f'{s}px' for s in sizes)} "
              f"on {a.background or '#FFFFFF'} -> {a.out}")
        return 0

    # NEVER DISTORT. Until 2026-09-12 the cell was shaped from the FIRST image and every
    # image was hard-resized into it, so a sheet mixing orientations stretched everything
    # that did not match. Measured on a real sheet: a 1024x1536 plate first, then two
    # 1536x1024 frames squashed into a portrait cell, a 2.25x aspect error.
    #
    # THAT IS A CORRECTNESS BUG, NOT A COSMETIC ONE, because this sheet is the surface a
    # human picks from. A distorted plate means a pick made on an image that is not the
    # image. The operator caught it by eye: "Results sheet shouldn't distort the images
    # like that."
    #
    # The cell is now shaped by the TALLEST aspect present, and every image is fitted
    # inside it preserving its own aspect and centred. On a sheet whose images all share
    # one shape, which is most of them, this is a no-op and reproduces the old output.
    sizes = [_open(p, ground).size for p in paths]
    cell_h = max(1, max(round(a.width * h / w) for w, h in sizes))
    pad = 22 if a.label else 0
    cols = max(1, min(a.cols or 2, len(paths)))
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (a.width * cols, (cell_h + pad) * rows), ground)
    draw = ImageDraw.Draw(sheet)
    for i, p in enumerate(paths):
        im = _open(p, ground)
        # Fit inside the cell rather than filling it: the scale is the tighter of the two
        # axes, so nothing is cropped either. Cropping would be the same lie as stretching,
        # told more quietly.
        k = min(a.width / im.size[0], cell_h / im.size[1])
        im = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))),
                       Image.LANCZOS)
        x, y = (i % cols) * a.width, (i // cols) * (cell_h + pad)
        # A faint grey behind the letterbox, so the image's TRUE BOUNDS are visible even
        # when the image itself has a white background. On a white sheet a white plate has
        # no edge, and not knowing where a plate ends is its own way of misreading it.
        # With --background the letterbox IS the surface's ground: the point is to see the
        # image's edge against what will actually be behind it.
        draw.rectangle([x, y + pad, x + a.width - 1, y + pad + cell_h - 1],
                       fill=ground if a.background else (238, 238, 238))
        sheet.paste(im, (x + (a.width - im.size[0]) // 2, y + pad + (cell_h - im.size[1]) // 2))
        if a.label:
            draw.text((x + 8, y + 6), os.path.basename(p), fill=_ink(ground))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    sheet.save(a.out)
    print(f"[contact-sheet] {len(paths)} image(s), {cols}x{rows} -> {a.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
