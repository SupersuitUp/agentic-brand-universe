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
        self.assertEqual((self.root / "marks/mark.svg").read_text().strip(), SVG.replace("'", '"'))  # re-serialized by the sanitizer
        self.assertEqual(self.j("universe.json")["identity"]["mark"], "marks/mark.svg")
        self.assertTrue((self.root / "canon/craft/brand-brief.md").exists())

    def test_board_becomes_anchor(self):
        board = Path(self.tmp.name) / "b.png"; board.write_bytes(b"\x89PNG\r\n\x1a\n fake")
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

    def test_favicon_wraps_a_bare_mark_on_the_accent(self):
        self.run_seed()
        fav = (self.root / "marks/favicon.svg").read_text()
        self.assertIn('viewBox="0 0 100 100"', fav)
        self.assertIn('fill="#c8743a"', fav)          # the accent tile
        self.assertIn("<text>WF</text>", fav)          # the mark rides inside it
        self.assertEqual(self.j("universe.json")["identity"]["favicon"], "marks/favicon.svg")

    def test_favicon_keeps_a_mark_that_has_its_own_background(self):
        own = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#123456"/><path d="M0 0L9 9Z" fill="#fff"/></svg>'
        seed.seed_universe(self.root, D, brief_md="b", mark_svg=own)
        self.assertEqual((self.root / "marks/favicon.svg").read_text().strip(), own)

    def test_favicon_is_well_formed_when_the_mark_has_its_own_size(self):
        import xml.dom.minidom as m
        bare = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="40" height="40"><path d="M0 0L9 9Z"/></svg>'
        seed.seed_universe(self.root, D, brief_md="b", mark_svg=bare)
        fav = (self.root / "marks/favicon.svg").read_text()
        m.parseString(fav)
        self.assertIn('viewBox="0 0 40 40"', fav)
        self.assertEqual(fav.count("width="), 3)  # outer svg, tile rect, nested mark: no duplicates

    def test_favicon_has_a_recipe(self):
        self.run_seed()
        r = json.loads((self.root / "marks/favicon.svg.recipe.json").read_text())
        self.assertEqual(r["generator"], "abu seed")

    def test_light_accent_validates(self):
        d = json.loads(json.dumps(D)); d["palette"]["lightAccent"] = "nope"
        self.assertTrue(any("palette.lightAccent" in e for e in validate_direction(d)))
        d["palette"]["lightAccent"] = "#a5552a"
        self.assertEqual(validate_direction(d), [])

    def test_artifact_light_uses_the_light_accent(self):
        d = json.loads(json.dumps(D)); d["palette"]["lightAccent"] = "#a5552a"
        self.run_seed(d)
        self.assertEqual(self.j("canon/craft/palette.json")["tokens"]["lightAccent"], "#a5552a")
        roles = self.j("universe.json")["identity"]["surfaces"]["artifact-light"]["roles"]
        self.assertEqual(roles["accent"], "lightAccent")

    def test_artifact_light_falls_back_to_accent_without_a_light_accent(self):
        self.run_seed()
        roles = self.j("universe.json")["identity"]["surfaces"]["artifact-light"]["roles"]
        self.assertEqual(roles["accent"], "accent")

    @unittest.skipUnless((Path.home() / ".freedom/bin/freedom-lib").exists(), "Supersuit not installed")
    def test_emit_artifact_light_returns_the_light_accent(self):
        import subprocess
        d = json.loads(json.dumps(D)); d["palette"]["lightAccent"] = "#a5552a"
        self.run_seed(d)
        out = subprocess.run([str(Path.home() / ".freedom/bin/freedom-lib"), "run", ".agents/lib/freedom-brand.mjs",
                              "emit", "--universe", str(self.root), "--surface", "artifact-light"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        e = json.loads(out.stdout)
        self.assertEqual((e["ground"], e["text"], e["accent"]), ("#f6f2ea", "#1a1a1a", "#a5552a"))

    def test_shared_direction_fixtures(self):
        fx = json.loads((ENGINE_DIR.parent / "skills/explore-a-personal-brand/tests/fixtures/directions.json").read_text())
        for v in fx["valid"]:
            self.assertEqual(validate_direction(v["direction"]), [], v["name"])
        for bad in fx["invalid"]:
            errs = validate_direction(bad["direction"])
            self.assertTrue(any(e.startswith(bad["expect"]) for e in errs), (bad["name"], errs))

    def test_seed_refuses_bad_inputs_before_writing_anything(self):
        before = sorted(p.name for p in self.root.rglob("*"))
        board = Path(self.tmp.name) / "b.png"
        for kw, msg in [
            (dict(mark_svg="not svg"), "mark"),
            (dict(mark_svg="<svg><"), "mark"),
            (dict(mark_svg=SVG, brief_md=""), "brief"),
            (dict(mark_svg=SVG, board_png=Path(self.tmp.name) / "missing.png"), "board"),
        ]:
            args = dict(brief_md="# b", board_png=None); args.update(kw)
            with self.assertRaises(ValueError) as cm:
                seed.seed_universe(self.root, D, **args)
            self.assertIn(msg, str(cm.exception))
        board.write_bytes(b"GIF89a not a png")
        with self.assertRaises(ValueError):
            seed.seed_universe(self.root, D, brief_md="# b", board_png=board, mark_svg=SVG)
        self.assertEqual(sorted(p.name for p in self.root.rglob("*")), before)

    def test_mark_is_sanitized(self):
        evil = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" onload="x()">'
                '<script>alert(1)</script><foreignObject><div>hi</div></foreignObject>'
                '<a href="javascript:alert(1)"><path d="M0 0L9 9Z" onclick="y()"/></a></svg>')
        seed.seed_universe(self.root, D, brief_md="b", mark_svg=evil)
        for rel in ("marks/mark.svg", "marks/favicon.svg"):
            t = (self.root / rel).read_text().lower()
            for bad in ("<script", "foreignobject", "onload", "onclick", "javascript:"):
                self.assertNotIn(bad, t, (rel, bad))
            self.assertIn("<path", t)

    def test_hex_with_a_trailing_newline_is_refused(self):
        d = json.loads(json.dumps(D)); d["palette"]["ground"] = "#101418\n"
        self.assertTrue(any("palette.ground" in e for e in validate_direction(d)))

    def test_universe_still_validates(self):
        from agenticstory.store import CanonStore
        self.run_seed()
        self.assertEqual(CanonStore(self.root).validate_canon(), [])


if __name__ == "__main__":
    unittest.main()
