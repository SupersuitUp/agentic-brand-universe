"""glyph-paths.py: outline letters from a Google Fonts family, including single-weight families."""
import importlib.util
import io
import sys
import unittest
import urllib.error
from pathlib import Path

try:
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    HAVE_FT = True
except ImportError:  # the script itself runs under `uv run --with fonttools`
    HAVE_FT = False

SCRIPT = Path(__file__).resolve().parents[2] / "skills/explore-a-personal-brand/scripts/glyph-paths.py"


def load():
    spec = importlib.util.spec_from_file_location("glyph_paths", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def tiny_font_bytes():
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", "S"])
    fb.setupCharacterMap({ord("S"): "S"})
    pen = TTGlyphPen(None); pen.moveTo((0, 0)); pen.lineTo((0, 700)); pen.lineTo((500, 700)); pen.closePath()
    notdef = TTGlyphPen(None); notdef.moveTo((0, 0)); notdef.lineTo((0, 10)); notdef.lineTo((10, 10)); notdef.closePath()
    fb.setupGlyf({".notdef": notdef.glyph(), "S": pen.glyph()})
    fb.setupHorizontalMetrics({".notdef": (500, 0), "S": (600, 0)})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Tiny", "styleName": "Regular"})
    fb.setupOS2(); fb.setupPost()
    buf = io.BytesIO(); fb.save(buf)
    return buf.getvalue()


@unittest.skipUnless(HAVE_FT, "fontTools not installed")
class GlyphPathsTest(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.font = tiny_font_bytes()
        self.requests = []

        def fake_fetch(url):
            self.requests.append(url)
            if url.startswith("https://fonts.googleapis.com/"):
                if "wght%40600" in url or "wght@600" in url:
                    raise urllib.error.HTTPError(url, 400, "Bad Request", {}, None)   # single-weight family
                return b"@font-face { src: url(https://fonts.gstatic.com/x.ttf) format('truetype'); }"
            return self.font
        self.m.fetch = fake_fetch

    def test_a_single_weight_family_is_retried_without_the_weight_axis(self):
        font = self.m.load_font("Bebas Neue", 600, "S")
        self.assertIn(ord("S"), font.getBestCmap())
        css_urls = [u for u in self.requests if "googleapis" in u]
        self.assertEqual(len(css_urls), 2)
        self.assertIn("wght", css_urls[0])
        self.assertNotIn("wght", css_urls[1])

    def test_a_missing_family_still_fails_clearly(self):
        def always_404(url):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        self.m.fetch = always_404
        with self.assertRaises(SystemExit) as cm:
            self.m.load_font("Nope Sans", 600, "S")
        self.assertIn("Google", str(cm.exception))

    def test_script_does_not_install_packages_at_runtime(self):
        text = SCRIPT.read_text()
        self.assertNotIn("subprocess", text)
        self.assertNotIn("pip install", text)


if __name__ == "__main__":
    unittest.main()
