"""`abu seed`: a direction becomes a universe's brand, readable by freedom-brand.mjs."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_DIR))

from agenticstory import scaffold, seed  # noqa: E402
from agenticstory.direction import validate_direction  # noqa: E402

D = {
    "name": "Night Workshop", "concept": "one line",
    "palette": {"ground": "#101418", "ink": "#e9e4da", "accent": "#c8743a",
                "lightGround": "#f6f2ea", "lightInk": "#1a1a1a"},
    "type": {"display": "Fraunces", "body": "Inter"},
    "mark": {"kind": "monogram", "letters": "WF", "treatment": "serif-ligature"},
    "sources": [],
}
SVG = "<svg xmlns='http://www.w3.org/2000/svg'><text>WF</text></svg>"


class SeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "u"
        scaffold.scaffold_universe(self.root, name="night-workshop")

    def tearDown(self):
        self.tmp.cleanup()

    def run_seed(self, d=D, board=None):
        return seed.seed_universe(self.root, d, brief_md="# Brief\n", board_png=board, mark_svg=SVG)

    def j(self, rel):
        return json.loads((self.root / rel).read_text())

    def test_palette_tokens(self):
        self.run_seed()
        t = self.j("canon/craft/palette.json")["tokens"]
        self.assertEqual((t["ground"], t["ink"], t["accent"]), ("#101418", "#e9e4da", "#c8743a"))
        self.assertEqual((t["lightGround"], t["lightInk"]), ("#f6f2ea", "#1a1a1a"))

    def test_no_light_tokens_when_not_given(self):
        d = json.loads(json.dumps(D)); del d["palette"]["lightGround"], d["palette"]["lightInk"]
        self.run_seed(d)
        self.assertNotIn("lightGround", self.j("canon/craft/palette.json")["tokens"])
        self.assertNotIn("artifact-light", self.j("universe.json")["identity"]["surfaces"])

    def test_surfaces(self):
        self.run_seed()
        s = self.j("universe.json")["identity"]["surfaces"]
        want = {"tokens": "canon/craft/palette.json#tokens",
                "roles": {"ground": "ground", "text": "ink", "accent": "accent"},
                "display": "Fraunces"}
        self.assertEqual(s["default"], want)
        self.assertEqual(s["artifact"], want)
        self.assertEqual(s["artifact-light"]["roles"]["ground"], "lightGround")

    def test_type(self):
        self.run_seed()
        t = self.j("canon/craft/type.json")
        self.assertEqual((t["display"], t["body"]), ("Fraunces", "Inter"))
        self.assertTrue(t["fontsUrl"].startswith("https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600&family=Inter"))

    def test_font_with_space(self):
        self.assertIn("family=Playfair+Display:", seed.fonts_url("Playfair Display", "Inter"))

    def test_mark_and_brief(self):
        self.run_seed()
        self.assertEqual((self.root / "marks/mark.svg").read_text(), SVG)
        self.assertEqual(self.j("universe.json")["identity"]["mark"], "marks/mark.svg")
        self.assertTrue((self.root / "canon/craft/brand-brief.md").exists())

    def test_board_becomes_anchor(self):
        board = Path(self.tmp.name) / "b.png"; board.write_bytes(b"\x89PNG fake")
        self.run_seed(board=board)
        self.assertEqual(self.j("universe.json")["identity"]["register"]["anchor"],
                         "reference/register/board.png")
        self.assertTrue((self.root / "reference/register/board.png").exists())

    def test_invalid_hex_names_field(self):
        d = json.loads(json.dumps(D)); d["palette"]["accent"] = "orange"
        errs = validate_direction(d)
        self.assertTrue(any("palette.accent" in e for e in errs))
        with self.assertRaises(ValueError) as cm:
            self.run_seed(d)
        self.assertIn("palette.accent", str(cm.exception))

    def test_every_file_has_recipe(self):
        written = self.run_seed()
        files = [Path(p) for p in written if not p.endswith(".recipe.json") and not p.endswith("universe.json")]
        self.assertTrue(files)
        for f in files:
            r = f.with_name(f.name + ".recipe.json")
            self.assertTrue(r.exists(), r)
            self.assertEqual(json.loads(r.read_text())["generator"], "abu seed")

    def test_universe_still_validates(self):
        from agenticstory.store import CanonStore
        self.run_seed()
        self.assertEqual(CanonStore(self.root).validate_canon(), [])


if __name__ == "__main__":
    unittest.main()
