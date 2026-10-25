"""The kit (SPEC §13.1, v0.60): pieces and no-gos, validated by `validate` and enforced by
`check-kit`. Earned 2026-10-06 on continental-works, where Gary rejected the six stripes run
down one edge of a selected card and asked that ABU catalog "all these different Lego pieces of
the brand and no-goes".
"""
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from agenticstory.cli import main
from agenticstory.kit import scan
from agenticstory.store import CanonStore

ASCENT = {
    "id": "the-ascent", "kind": "register-rule", "name": "A", "summary": "s",
    "rules": ["ONE CONTINUOUS RIBBON, NEVER DISCONNECTED PIECES. Gary: 'I don't love the rainbow disconnected'."],
    "tokens": {"teal": {"hex": "#105971"}, "mustard": {"hex": "#E9A23B"}, "tomato": {"hex": "#DB371F"}},
    "icon": {"rules": ["six stripes at 64px and up; three (teal, mustard, tomato) at 36 to 48px"]},
    "surfaces": {"frapp": {"roles": {"chosenOption": "the selection ring (brand-kit selection-ring)"}}},
}

# The two shapes the no-go was written against, as they shipped.
READER_CSS = """.pick button[aria-checked="true"]{background-color:var(--card);border-color:var(--teal);color:var(--ink);background-image:var(--ribbon-across);background-repeat:no-repeat;background-size:12px 100%;padding-left:18px}
"""
FRAPP_STYLE = """const css = `
.opts label:has(input:checked)::before{content:"";position:absolute;inset:0 auto 0 0;width:.55rem;background:var(--ribbon-edge)}
`;
"""
RING_CSS = """.pick button[aria-checked="true"]{background-color:var(--card);border-color:var(--teal);box-shadow:var(--ring)}
.ribbon i:nth-child(1){background:var(--stripe-1)}
"""
DETECT = [
    {"pattern": r"""(?:checked|selected|chosen)[^{}]*\{(?=[^}]*(?:ribbon|stripe))(?=[^}]*background-size:\s*[\d.]+(?:px|rem|em)\s+100%)""",
     "note": "a striped background sized to a narrow strip inside the chosen element"},
    {"pattern": r"""(?:checked|selected|chosen)[^{}]*::?(?:before|after)\s*\{(?=[^}]*(?:ribbon|stripe))(?=[^}]*(?:inset:\s*0\s+auto\s+0\s+0|left:\s*0))""",
     "note": "a striped pseudo-element bar pinned to the chosen element's edge"},
]


def kit(**over):
    k = {
        "id": "brand-kit", "kind": "kit", "name": "Kit", "summary": "pieces and no-gos",
        "tokensFrom": "canon/craft/the-ascent.json#tokens",
        "pieces": [{
            "id": "selection-ring", "name": "The selection ring", "for": "marking the chosen option",
            "recipe": {"tokens": ["teal", "mustard", "tomato"],
                       "css": "border:2px solid teal; box-shadow: inset 0 0 0 2px mustard, inset 0 0 0 4px tomato"},
            "definedAt": "canon/craft/the-ascent.json#icon.rules.0",
            "decided": {"by": "Gary Sheng", "on": "2026-10-06", "verbatim": "make it like a full multi-border"},
        }],
        "noGos": [{
            "id": "edge-stripe-on-selection", "refuses": "stripes down one edge of a selected element",
            "why": "it reads as a tab, not a choice", "instead": "selection-ring",
            "decided": {"by": "Gary Sheng", "on": "2026-10-06", "verbatim": "I really don't like it"},
            "supersedes": [{"at": "canon/craft/the-ascent.json#surfaces.frapp.roles.chosenOption",
                            "said": "the six-stripe ribbon down its leading edge"}],
            "detect": DETECT,
        }, {
            "id": "disconnected-ribbon-pieces", "refuses": "a stripe flourish not connected to the ribbon",
            "why": "there is one ribbon", "instead": None, "insteadNote": "extend the one ribbon",
            "decided": {"by": "Gary Sheng", "on": "2026-09-28"},
            "source": [{"at": "canon/craft/the-ascent.json#rules.0", "quote": "ONE CONTINUOUS RIBBON, NEVER DISCONNECTED PIECES"}],
        }],
    }
    k.update(over)
    return k


class KitTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="abu-kit-"))
        (self.dir / "canon" / "entities").mkdir(parents=True)
        (self.dir / "canon" / "craft").mkdir(parents=True)
        (self.dir / "universe.json").write_text(json.dumps({"id": "t", "name": "T", "assetRoot": ".", "identity": {}}))
        self.write_ascent(ASCENT)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_ascent(self, rec):
        (self.dir / "canon" / "craft" / "the-ascent.json").write_text(json.dumps(rec))

    def problems(self, k):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(k))
        return [p for p in CanonStore(self.dir).validate_canon() if "kit" in p]

    def test_a_sound_kit_validates(self):
        self.assertEqual(self.problems(kit()), [])

    def test_no_kit_is_fine(self):
        self.assertEqual([p for p in CanonStore(self.dir).validate_canon() if "kit" in p], [])

    def test_instead_must_name_a_piece(self):
        k = kit(); k["noGos"][0]["instead"] = "selection-halo"
        self.assertTrue(any("not a piece in any kit" in p for p in self.problems(k)))

    def test_null_instead_needs_a_note(self):
        k = kit(); k["noGos"][1].pop("insteadNote")
        self.assertTrue(any("insteadNote" in p for p in self.problems(k)))

    def test_a_no_go_that_names_a_file_needs_a_detector(self):
        # 2026-10-25: the CW ribbon mark was a no-go naming its file, with only a detectNote,
        # and shipped again the same week in a new lockup that nothing flagged.
        k = kit(); k["noGos"][1]["refuses"] = "the retired mark, public/brand/cw-mark.svg"
        self.assertTrue(any("names a file" in p for p in self.problems(k)))
        k["noGos"][1]["detect"] = [{"pattern": "cw-mark\\.svg", "note": "the retired file"}]
        self.assertFalse(any("names a file" in p for p in self.problems(k)))

    def test_a_ruling_with_no_provenance_is_refused(self):
        k = kit(); k["pieces"][0].pop("decided")
        self.assertTrue(any("'decided' is missing" in p for p in self.problems(k)))
        k = kit(); k["noGos"][0]["decided"] = {"by": "Gary Sheng", "on": "Oct 6"}
        got = "\n".join(self.problems(k))
        self.assertIn("YYYY-MM-DD", got)
        self.assertIn("verbatim is missing", got)

    def test_a_harvested_quote_must_still_be_in_canon(self):
        rec = json.loads(json.dumps(ASCENT)); rec["rules"] = ["One ribbon."]
        self.write_ascent(rec)
        self.assertTrue(any("no longer says" in p for p in self.problems(kit())))

    def test_a_superseded_line_that_still_says_the_old_thing_is_refused(self):
        rec = json.loads(json.dumps(ASCENT))
        rec["surfaces"]["frapp"]["roles"]["chosenOption"] = "teal border plus the six-stripe ribbon down its leading edge"
        self.write_ascent(rec)
        self.assertTrue(any("STILL says" in p for p in self.problems(kit())))

    def test_a_piece_needs_a_recipe_or_a_pointer_that_resolves(self):
        k = kit(); k["pieces"][0].pop("recipe"); k["pieces"][0]["definedAt"] = "canon/craft/the-ascent.json#icon.rules.9"
        got = "\n".join(self.problems(k))
        self.assertIn("does not resolve", got)
        k = kit(); k["pieces"][0].pop("recipe"); k["pieces"][0].pop("definedAt")
        self.assertTrue(any("'recipe' or a 'definedAt'" in p for p in self.problems(k)))

    def test_recipe_tokens_are_checked(self):
        k = kit(); k["pieces"][0]["recipe"]["tokens"].append("gold")
        self.assertTrue(any("recipe token 'gold'" in p for p in self.problems(k)))

    def test_duplicate_ids_and_bad_patterns_are_refused(self):
        k = kit(); k["noGos"][1]["id"] = "selection-ring"; k["noGos"][0]["detect"] = [{"pattern": "(unclosed"}]
        got = "\n".join(self.problems(k))
        self.assertIn("already used", got)
        self.assertIn("does not compile", got)

    def test_a_sibling_repo_source_is_recorded_not_checked(self):
        k = kit(); k["noGos"][1]["source"].append({"at": "other-repo:STATE.md@abc123", "quote": "no italics"})
        self.assertEqual(self.problems(k), [])

    def _surface(self):
        site = self.dir / "site"
        (site / "node_modules" / "x").mkdir(parents=True)
        (site / "reader.css").write_text(READER_CSS)
        (site / "frapp-style.mjs").write_text(FRAPP_STYLE)
        (site / "ring.css").write_text(RING_CSS)
        (site / "node_modules" / "x" / "skip.css").write_text(READER_CSS)
        return site

    def test_scan_finds_both_shipped_shapes_and_passes_the_ring(self):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        hits = scan(CanonStore(self.dir).craft, [str(self._surface())])
        files = sorted(Path(h["file"]).name for h in hits)
        self.assertEqual(files, ["frapp-style.mjs", "reader.css"])
        self.assertTrue(all(h["nogo"] == "edge-stripe-on-selection" and h["instead"] == "selection-ring" for h in hits))
        self.assertEqual([h["line"] for h in hits if h["file"].endswith(".mjs")], [2])

    def test_check_kit_exit_codes(self):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        site = self._surface()
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["check-kit", str(self.dir), str(site)]), 1)
        self.assertIn("NO-GO edge-stripe-on-selection", out.getvalue())
        self.assertIn("The selection ring", out.getvalue())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["check-kit", str(self.dir), str(site / "ring.css")]), 0)
        k = kit(); k["noGos"][0].pop("detect"); k.pop("tokensFrom")
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(k))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["check-kit", str(self.dir), str(site)]), 2)

    # ---- the palette (v0.61): a colour the token file does not hold is refused ----
    def test_off_palette_colours_are_refused_and_tokens_pass(self):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        site = self.dir / "pal"; site.mkdir()
        (site / "ok.css").write_text(".a{color:#105971;background:#fff;border-color:rgba(233,162,59,.4)}\n.b{color:#e9a23b80}\n")
        (site / "bad.tsx").write_text('const a = "x";\nconst s = { boxShadow: "0 1px 2px rgba(30,25,20,0.5)", color: "#123456" };\n<a href="#top">up</a>\n<div className="ring-1 ring-black/5 shadow-[0_2px_8px_rgba(10,11,12,0.5)] bg-(--r-teal)" />\n')
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["check-kit", str(self.dir), str(site)]), 1)
        got = out.getvalue()
        self.assertIn("OFF-PALETTE #1E1914", got)
        self.assertIn("OFF-PALETTE #123456", got)
        self.assertIn("OFF-PALETTE ring-black/5", got, "a Tailwind palette class is a colour the universe never chose")
        self.assertIn("OFF-PALETTE #0A0B0C", got, "an rgba inside a Tailwind arbitrary value still counts")
        self.assertNotIn("ok.css", got, "tokens, white and a token with alpha are on the palette")
        self.assertNotIn("#TOP", got.upper().replace("#TOP\">", ""), "an anchor is not a colour")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["check-kit", str(self.dir), str(site), "--no-palette"]), 0)

    def test_a_colour_named_in_prose_is_not_on_the_palette(self):
        """Regression, 2026-10-14: the Continental Works record's prose names #007AFF as a colour
        it REFUSES, and the palette used to take every hex written anywhere in the file, so the
        refused colour passed. Only colour VALUES count: a token's `hex`, a derived `hex`, or a
        string that is nothing but a hex."""
        rec = dict(ASCENT)
        rec["rules"] = ASCENT["rules"] + ["Never the system blue #007AFF, the derived greys, or the old cream #F0ECE5."]
        rec["tokens"] = dict(ASCENT["tokens"], teal={"hex": "#105971", "role": "stripe 1; was #0F5A70 until a week ago"})
        rec["surfaces"] = dict(ASCENT["surfaces"], frapp=dict(ASCENT["surfaces"]["frapp"],
                               derived={"paper": {"hex": "#FBF5E7", "mix": ["cream", "white", 0.42]}}))
        rec["accent"] = "#AABBCC"
        self.write_ascent(rec)
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        site = self.dir / "pal"; site.mkdir()
        (site / "bad.css").write_text(".btn{background:#007AFF}\n.c{color:#F0ECE5}\n.d{color:#0F5A70}\n")
        (site / "ok.css").write_text(".a{color:#105971;background:#fff}\n.b{color:#FBF5E7}\n.e{color:#aabbcc}\n.f{color:#E9A23B}\n")
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["check-kit", str(self.dir), str(site)]), 1)
        got = out.getvalue()
        self.assertIn("OFF-PALETTE #007AFF", got, "a colour the record names in prose to refuse it is refused")
        self.assertIn("OFF-PALETTE #F0ECE5", got)
        self.assertIn("OFF-PALETTE #0F5A70", got, "a superseded value quoted in a token's role is not a token")
        self.assertNotIn("ok.css", got, "token hexes, a derived hex, a bare hex value and white still pass")

    def _git(self, repo, *a):
        import subprocess
        subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)

    def test_added_judges_only_what_the_range_adds(self):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        repo = self.dir / "surface"; repo.mkdir()
        self._git(repo, "init", "-q"); self._git(repo, "config", "user.email", "t@t"); self._git(repo, "config", "user.name", "t")
        (repo / "old.css").write_text(".old{color:#abcdef}\n")
        self._git(repo, "add", "."); self._git(repo, "commit", "-qm", "old debt")
        (repo / "old.css").write_text(".old{color:#abcdef}\n.new{color:#105971}\n")
        (repo / "new.css").write_text(".n{color:#00ff00}\n")
        self._git(repo, "add", "."); self._git(repo, "commit", "-qm", "the push")
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["check-kit", str(self.dir), str(repo), "--added", "HEAD~1..HEAD"]), 1)
        self.assertIn("#00FF00", out.getvalue())
        self.assertNotIn("#ABCDEF", out.getvalue(), "old debt on an untouched line is not this push's")
        (repo / "new.css").write_text(".n{color:#105971}\n")
        self._git(repo, "commit", "-qam", "fixed")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["check-kit", str(self.dir), str(repo), "--added", "HEAD~1..HEAD"]), 0)

    def test_baseline_tolerates_old_findings_and_refuses_new_ones(self):
        import os
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        site = self.dir / "b"; site.mkdir()
        (site / "a.css").write_text(".x{color:#abcdef}\n.y{color:#abcdef}\n")
        here = os.getcwd(); os.chdir(site)
        try:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["check-kit", str(self.dir), "a.css", "--write-baseline", "base.json"]), 0)
                self.assertEqual(main(["check-kit", str(self.dir), "a.css", "--baseline", "base.json"]), 0)
            # Lines move: still tolerated. A new colour, or a third copy of an old one: refused.
            (site / "a.css").write_text("/* moved */\n.x{color:#abcdef}\n.y{color:#abcdef}\n.z{color:#00ff00}\n.y{color:#abcdef}\n")
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(main(["check-kit", str(self.dir), "a.css", "--baseline", "base.json"]), 1)
            self.assertIn("#00FF00", out.getvalue())
            self.assertEqual(out.getvalue().count("#ABCDEF"), 1, "two recorded copies excuse two, not three")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["check-kit", str(self.dir), "a.css", "--baseline", "missing.json"]), 2)
        finally:
            os.chdir(here)

    def test_added_outside_git_cannot_judge(self):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        loose = Path(tempfile.mkdtemp(prefix="abu-loose-"))
        (loose / "a.css").write_text(".a{color:#00ff00}\n")
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["check-kit", str(self.dir), str(loose), "--added", "HEAD~1..HEAD"]), 2)
        self.assertIn("not inside a git repository", out.getvalue())
        shutil.rmtree(loose, ignore_errors=True)

    def test_kit_verb_lists(self):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["kit", str(self.dir)]), 0)
        self.assertIn("piece  selection-ring", out.getvalue())
        self.assertIn("no-go  edge-stripe-on-selection", out.getvalue())

    # ---- waivers (v1.45): a reasoned `abu-allow:` lets one line through, and is counted ----
    # Earned 2026-10-14: an iMessage simulator on continentalworks.ai must keep the real iOS blue,
    # which the brand refuses as a BRAND colour. Gary: "people should be able to skip the
    # warnings ... and then be able to quickly file a bug".
    def _check(self, *extra, files):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        site = self.dir / "w"; site.mkdir(exist_ok=True)
        for name, text in files.items():
            (site / name).write_text(text)
        with redirect_stdout(io.StringIO()) as out:
            code = main(["check-kit", str(self.dir), str(site), *extra])
        return code, out.getvalue()

    def test_a_reasoned_waiver_on_the_line_lets_it_through_and_is_counted(self):
        code, got = self._check(files={"sim.css": ".bubble{background:#007AFF} /* abu-allow: iOS Messages mockup */\n"})
        self.assertEqual(code, 0, got)
        self.assertIn("clean, 1 waived", got, "a skip is never silent")

    def test_a_waiver_on_the_line_above_covers_the_next_line_only(self):
        code, got = self._check(files={"sim.tsx": "// abu-allow: iOS Messages mockup\nconst blue = '#007AFF';\nconst also = '#123456';\n"})
        self.assertEqual(code, 1)
        self.assertIn("OFF-PALETTE #123456", got)
        self.assertNotIn("#007AFF", got)
        self.assertIn("1 waived", got)

    def test_a_waiver_with_no_reason_waives_nothing_and_says_why(self):
        code, got = self._check(files={"sim.css": ".bubble{background:#007AFF} /* abu-allow: */\n"})
        self.assertEqual(code, 1)
        self.assertIn("OFF-PALETTE #007AFF", got)
        self.assertIn("abu-allow needs a reason", got)

    def test_every_refusal_says_how_to_skip_it_or_report_it(self):
        code, got = self._check(files={"bad.css": ".x{color:#123456}\n"})
        self.assertEqual(code, 1)
        self.assertIn("abu-allow: <why>", got)
        self.assertIn("abu report", got)

    def test_a_waived_line_never_enters_a_baseline(self):
        import os
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        site = self.dir / "wb"; site.mkdir()
        (site / "a.css").write_text(".x{color:#007AFF} /* abu-allow: mockup */\n.y{color:#abcdef}\n")
        here = os.getcwd(); os.chdir(site)
        try:
            with redirect_stdout(io.StringIO()):
                main(["check-kit", str(self.dir), "a.css", "--write-baseline", "base.json"])
            rows = json.loads((site / "base.json").read_text())["findings"]
        finally:
            os.chdir(here)
        self.assertEqual([r["value"] for r in rows], ["#ABCDEF"])

    def test_check_kit_report_carries_the_findings_and_the_rule(self):
        from urllib.parse import urlparse, parse_qs
        code, got = self._check("--report", files={"reader.css": READER_CSS, "bad.css": ".x{color:#123456}\n"})
        self.assertEqual(code, 1)
        url = [l for l in got.split("\n") if l.startswith("https://github.com/")][0]
        q = parse_qs(urlparse(url).query)
        body = q["body"][0]
        self.assertTrue(urlparse(url).path.endswith("/issues/new"))
        self.assertIn("check-kit", q["title"][0])
        for want in ("edge-stripe-on-selection", "it reads as a tab, not a choice", "I really don't like it",
                     "The selection ring", "reader.css:1", "OFF-PALETTE #123456", "bad.css:1",
                     "What I expected", "ABU version", "Python", "check-kit"):
            self.assertIn(want, body, f"the issue must carry {want!r}")


if __name__ == "__main__":
    unittest.main()
