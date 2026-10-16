#!/usr/bin/env python3
"""The contact sheet must refuse a partial set rather than quietly shrink.

A short sheet reads as "everything I rendered", which is exactly how a missing spread
goes unnoticed. One spread of gain-everything-lose-nothing was parked mid-batch and its
absence was only caught by counting files by hand (2026-07-30).
"""
import os, pathlib, subprocess, sys, tempfile, unittest
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "contact_sheet.py"


def _png(p, w=80, h=60, tint=(200, 180, 140)):
    from PIL import Image
    Image.new("RGB", (w, h), tint).save(p)


def _run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + args, capture_output=True, text=True)


class TestContactSheet(unittest.TestCase):
    def test_builds_a_labelled_sheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            imgs = []
            for i in range(4):
                p = os.path.join(tmp, f"spread-0{i+1}.png"); _png(p); imgs.append(p)
            out = os.path.join(tmp, "sheet.png")
            r = _run(imgs + ["--out", out])
            self.assertEqual(r.returncode, 0, r.stderr)
            from PIL import Image
            self.assertEqual(Image.open(out).size[0], 690 * 2, "default is a 2-up grid")

    def test_refuses_a_partial_sheet_and_names_what_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = os.path.join(tmp, "spread-01.png"); _png(good)
            missing = os.path.join(tmp, "spread-02.png")
            out = os.path.join(tmp, "sheet.png")
            r = _run([good, missing, "--out", out])
            self.assertEqual(r.returncode, 1, "a missing render must fail the sheet")
            self.assertIn("spread-02.png", r.stderr, "it must name what is missing")
            self.assertFalse(os.path.exists(out), "no sheet should be written at all")

    def test_cols_and_width_are_honoured(self):
        with tempfile.TemporaryDirectory() as tmp:
            imgs = []
            for i in range(3):
                p = os.path.join(tmp, f"s{i}.png"); _png(p); imgs.append(p)
            out = os.path.join(tmp, "sheet.png")
            r = _run(imgs + ["--out", out, "--cols", "3", "--width", "100"])
            self.assertEqual(r.returncode, 0, r.stderr)
            from PIL import Image
            self.assertEqual(Image.open(out).size[0], 300)


class AspectRatio(unittest.TestCase):
    """The defect that shipped: a sheet mixing orientations stretched every image that did
    not match the FIRST one's shape. None of the tests above caught it, because they all
    used one shape. A contact sheet is the surface a human picks from, so a distorted plate
    means a pick made on an image that is not the image.
    """

    def _sheet(self, sizes, **kw):
        d = pathlib.Path(tempfile.mkdtemp())
        paths = []
        # One solid colour per image, so each can be found in the output by its own colour
        # and measured. Distortion then shows up as a changed aspect of that colour region.
        colours = [(220, 20, 20), (20, 200, 20), (20, 20, 220), (220, 200, 20)]
        for n, (w, h) in enumerate(sizes):
            f = d / f"i{n}.png"
            Image.new("RGB", (w, h), colours[n % len(colours)]).save(f)
            paths.append(str(f))
        out = d / "sheet.png"
        cmd = [sys.executable, str(SCRIPT), *paths, "--out", str(out)]
        for k, v in kw.items():
            cmd += [f"--{k}", str(v)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return Image.open(out).convert("RGB"), colours

    def _region(self, im, colour):
        px = im.load()
        xs, ys = [], []
        for y in range(im.size[1]):
            for x in range(im.size[0]):
                c = px[x, y]
                if sum(abs(c[i] - colour[i]) for i in range(3)) < 40:
                    xs.append(x); ys.append(y)
        self.assertTrue(xs, f"colour {colour} not found in the sheet at all")
        return (max(xs) - min(xs) + 1), (max(ys) - min(ys) + 1)

    def test_MIXED_ORIENTATIONS_ARE_NOT_DISTORTED(self):
        """A portrait first, then a landscape: the exact shape of the real sheet that was
        caught by eye. 1024x1536 then 1536x1024 is a 2.25x aspect error when stretched."""
        im, cols = self._sheet([(1024, 1536), (1536, 1024)], cols=2)
        for n, (sw, sh) in enumerate([(1024, 1536), (1536, 1024)]):
            w, h = self._region(im, cols[n])
            got, want = w / h, sw / sh
            self.assertAlmostEqual(got, want, delta=0.04,
                                   msg=f"image {n} arrived at aspect {got:.3f}, source is "
                                       f"{want:.3f}: the sheet distorted it")

    def test_landscape_first_then_portrait(self):
        """The same defect in the other order, which is the one a fix keyed on the first
        image's orientation would still get wrong."""
        im, cols = self._sheet([(1536, 1024), (1024, 1536)], cols=2)
        for n, (sw, sh) in enumerate([(1536, 1024), (1024, 1536)]):
            w, h = self._region(im, cols[n])
            self.assertAlmostEqual(w / h, sw / sh, delta=0.04, msg=f"image {n} distorted")

    def test_nothing_is_cropped_either(self):
        """Cropping to fill the cell is the same lie as stretching, told more quietly: the
        full image must be present, so its scaled area must match what the fit predicts."""
        im, cols = self._sheet([(1024, 1536), (1536, 1024)], cols=2, width=400)
        w, h = self._region(im, cols[1])
        # The landscape image fits by WIDTH in a portrait-shaped cell.
        self.assertAlmostEqual(w, 400, delta=2)

    def test_uniform_sheet_still_fills_the_cell(self):
        """The fix must be a no-op when every image shares one shape, which is most sheets.
        A letterbox that shrinks a uniform sheet would have changed every existing one."""
        im, cols = self._sheet([(1024, 1536), (1024, 1536)], cols=2, width=400)
        w, h = self._region(im, cols[0])
        self.assertAlmostEqual(w, 400, delta=2)
        self.assertAlmostEqual(h, 600, delta=2)


class CoverTheWholeBatch(unittest.TestCase):
    """The refusal `shoot-references` already claimed this script had (v0.49).

    Its SKILL.md says the sheet "already refuses a partial one, so a short sheet cannot
    read as 'everything I rendered'". That was true only of a file that did not EXIST.
    Nothing knew what the batch was, so three of twelve renders built a sheet happily and
    read, to the person looking at it, as twelve.
    """

    def batch(self, tmp, n=4):
        return [os.path.join(tmp, f"shot-{i}.png") for i in range(n)]

    def test_a_short_sheet_is_refused_and_names_what_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            shots = self.batch(tmp)
            for s in shots:
                _png(s)
            r = _run(shots[:2] + ["--out", os.path.join(tmp, "sheet.png"), "--cover", tmp])
            self.assertEqual(r.returncode, 1)
            self.assertIn("REFUSING a partial sheet", r.stderr)
            self.assertIn("shot-2.png", r.stderr)
            self.assertIn("shot-3.png", r.stderr)
            self.assertFalse(os.path.exists(os.path.join(tmp, "sheet.png")),
                             "a refused sheet must not be written")

    def test_a_complete_sheet_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            shots = self.batch(tmp)
            for s in shots:
                _png(s)
            out = os.path.join(tmp, "sheet.png")
            r = _run(shots + ["--out", out, "--cover", tmp])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(out))

    def test_the_sheet_being_written_into_the_batch_dir_is_not_itself_a_shot(self):
        """Otherwise the first run poisons the second: the sheet becomes a missing shot."""
        with tempfile.TemporaryDirectory() as tmp:
            shots = self.batch(tmp, 2)
            for s in shots:
                _png(s)
            out = os.path.join(tmp, "sheet.png")
            self.assertEqual(_run(shots + ["--out", out, "--cover", tmp]).returncode, 0)
            r = _run(shots + ["--out", out, "--cover", tmp])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_parked_candidate_is_history_not_a_shot(self):
        with tempfile.TemporaryDirectory() as tmp:
            shots = self.batch(tmp, 2)
            for s in shots:
                _png(s)
            _png(os.path.join(tmp, "shot-0-contact-sheet.png"))
            r = _run(shots + ["--out", os.path.join(tmp, "s.png"), "--cover", tmp])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_without_cover_nothing_changes(self):
        """The flag is opt-in: an existing caller building a deliberate subset still works."""
        with tempfile.TemporaryDirectory() as tmp:
            shots = self.batch(tmp)
            for s in shots:
                _png(s)
            r = _run(shots[:2] + ["--out", os.path.join(tmp, "sheet.png")])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_cover_dir_that_is_not_a_dir_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = os.path.join(tmp, "a.png")
            _png(s)
            r = _run([s, "--out", os.path.join(tmp, "o.png"), "--cover", s])
            self.assertEqual(r.returncode, 1)
            self.assertIn("not a directory", r.stderr)


class AtSizeOnTheSurfacesGround(unittest.TestCase):
    """`--at-size` and `--background`: judge a set at the size and on the ground it will live on.

    Issue #59, 2026-10-15. Reader portraits for a web book are shown at 64 px on #FBF5E7, and the
    ordinary sheet shows them at 690 px on white, so a direction could not be judged where it
    would be used. The run hand-rolled a script to render each set at 64 and 240 px on the paper.
    These tests measure the pixels: each image's footprint must be EXACTLY the asked size, and
    the ground must be EXACTLY the asked colour.
    """
    RED, BLUE = (220, 20, 20), (20, 20, 220)
    PAPER = (0xFB, 0xF5, 0xE7)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def img(self, name, size, colour, mode="RGB"):
        p = self.d / name
        Image.new(mode, size, colour).save(p)
        return str(p)

    def box(self, im, colour, tol=12):
        px = im.convert("RGB").load()
        w, h = im.size
        xs, ys = [], []
        for y in range(h):
            for x in range(w):
                r, g, b = px[x, y]
                if abs(r - colour[0]) <= tol and abs(g - colour[1]) <= tol and abs(b - colour[2]) <= tol:
                    xs.append(x); ys.append(y)
        return (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, len(xs)) if xs else (0, 0, 0)

    def sheet(self, *args):
        out = self.d / "at-size.png"
        r = _run(list(args) + ["--out", str(out)])
        self.assertEqual(r.returncode, 0, r.stderr)
        return Image.open(out)

    def test_each_image_appears_once_per_size_at_exactly_that_size(self):
        a = self.img("a.png", (512, 512), self.RED)
        sheet = self.sheet(a, "--at-size", "64", "--background", "#FBF5E7")
        w, h, n = self.box(sheet, self.RED)
        self.assertEqual((w, h), (64, 64))
        self.assertGreaterEqual(n, 64 * 64 - 64)

    def test_two_sizes_make_two_bands(self):
        a = self.img("a.png", (300, 300), self.RED)
        sheet = self.sheet(a, "--at-size", "64,240", "--background", "#FBF5E7")
        _, _, n = self.box(sheet, self.RED)
        self.assertAlmostEqual(n, 64 * 64 + 240 * 240, delta=300)

    def test_the_longest_edge_is_the_size_and_aspect_survives(self):
        a = self.img("wide.png", (400, 200), self.BLUE)
        sheet = self.sheet(a, "--at-size", "64", "--background", "#FBF5E7")
        w, h, _ = self.box(sheet, self.BLUE)
        self.assertEqual((w, h), (64, 32))

    def test_the_ground_is_the_asked_colour(self):
        a = self.img("a.png", (100, 100), self.RED)
        sheet = self.sheet(a, "--at-size", "64", "--background", "#FBF5E7")
        self.assertEqual(sheet.convert("RGB").getpixel((1, 1)), self.PAPER)
        self.assertEqual(sheet.convert("RGB").getpixel((sheet.size[0] - 2, sheet.size[1] - 2)),
                         self.PAPER)

    def test_transparency_shows_the_ground_not_black(self):
        a = self.img("cut.png", (100, 100), (0, 0, 0, 0), mode="RGBA")
        sheet = self.sheet(a, "--at-size", "64", "--background", "#FBF5E7")
        _, _, n_black = self.box(sheet, (0, 0, 0), tol=4)
        # labels are dark ink, but nowhere near a 64x64 block of it
        self.assertLess(n_black, 64 * 64 // 4)

    def test_background_alone_recolours_the_ordinary_sheet(self):
        a = self.img("a.png", (100, 50), self.RED)
        b = self.img("b.png", (50, 100), self.BLUE)
        sheet = self.sheet(a, b, "--background", "#FBF5E7", "--no-label")
        _, _, n_grey = self.box(sheet, (238, 238, 238), tol=2)
        self.assertEqual(n_grey, 0, "the grey letterbox must take the asked ground")
        self.assertEqual(sheet.convert("RGB").getpixel((0, 0)), self.PAPER)

    def test_without_the_flags_nothing_changes(self):
        a = self.img("a.png", (100, 50), self.RED)
        b = self.img("b.png", (50, 100), self.BLUE)
        sheet = self.sheet(a, b, "--no-label")
        self.assertEqual(sheet.size, (690 * 2, 1380))
        self.assertGreater(self.box(sheet, (238, 238, 238), tol=2)[2], 0)

    def test_a_bad_colour_is_refused(self):
        a = self.img("a.png", (10, 10), self.RED)
        r = _run([a, "--out", str(self.d / "o.png"), "--background", "cream"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--background", r.stderr)
        self.assertFalse((self.d / "o.png").exists())

    def test_a_bad_size_is_refused(self):
        a = self.img("a.png", (10, 10), self.RED)
        for bad in ("0", "abc", "64,-1"):
            r = _run([a, "--out", str(self.d / "o.png"), "--at-size", bad])
            self.assertNotEqual(r.returncode, 0, bad)
            self.assertIn("--at-size", r.stderr)

    def test_the_at_size_sheet_still_refuses_a_partial_set(self):
        a = self.img("a.png", (10, 10), self.RED)
        r = _run([a, str(self.d / "ghost.png"), "--out", str(self.d / "o.png"), "--at-size", "64"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("ghost.png", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
