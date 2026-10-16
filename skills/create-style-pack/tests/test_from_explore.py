"""create-style-pack --from-explore: an explore pick becomes a pack, with who picked and when.

Issue #60, 2026-10-15. After the operator picked one of three explore directions for three
made-up readers, promoting the pick was all by hand: move the drafts out of scratchpad, run the
scaffolder on hand-copied files, bless each ref, and write the scope as prose. These tests hold
the one-command path: the picked roll of every subject becomes a ref (byte-identical, recipe
beside it), each ref is blessed by the person who picked, pack.json records the pick, the
directions considered and the decision, and `--scope-use` writes a TYPED scope.
"""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve()
SCAFFOLD = HERE.parents[1] / "scripts" / "scaffold.py"
ENGINE = HERE.parents[3] / "engine"
PNG = b"\x89PNG\r\n\x1a\n"
SUBJECTS = ("diane", "jordan", "marcus")
DIRS = ("A-ascent-poster", "B-ink-line-wash", "C-warm-gouache")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


class FromExplore(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.t.name)
        self.explore = self.root / "explore"
        for s in SUBJECTS:
            d = self.explore / s
            d.mkdir(parents=True)
            for v in DIRS:
                (d / f"{v}.png").write_bytes(PNG + f"{s}-{v}".encode())
                (d / f"{v}.png.recipe.json").write_text(json.dumps({"prompt": f"{s} {v}"}))
                (d / f"{v}.prompt.txt").write_text("p")
            (d / "CONTACT-SHEET.png").write_bytes(PNG + b"sheet")
            (d / "AT-SIZE-SHEET.png").write_bytes(PNG + b"sheet2")
        self.pack = self.root / "pack"

    def tearDown(self):
        self.t.cleanup()

    def run_(self, *extra, base=True):
        args = [sys.executable, str(SCAFFOLD), "--dir", str(self.pack), "--id", "ascent-poster",
                "--name", "Ascent poster", "--style-line", "flat screen print",
                "--gate", "flat shapes only", "--text-policy", "none"]
        if base:
            args += ["--from-explore", str(self.explore), "--pick", "A-ascent-poster",
                     "--decided-by", "Gary Sheng", "--decided-on", "2026-10-15",
                     "--verbatim", "A · Ascent poster"]
        return subprocess.run(args + list(extra), capture_output=True, text=True)

    def manifest(self):
        return json.loads((self.pack / "pack.json").read_text())

    def test_every_subjects_pick_becomes_a_ref_named_for_the_subject(self):
        r = self.run_()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = self.manifest()
        self.assertEqual(m["refs"], [f"refs/{s}.png" for s in SUBJECTS])
        self.assertEqual(m["anchor"], "refs/diane.png")
        for s in SUBJECTS:
            self.assertEqual(sha(self.pack / "refs" / f"{s}.png"),
                             sha(self.explore / s / "A-ascent-poster.png"), "byte-identical")
            self.assertTrue((self.pack / "refs" / f"{s}.png.recipe.json").exists(),
                            "the recipe travels with the ref")

    def test_each_ref_is_blessed_by_who_picked_and_bound_to_its_bytes(self):
        self.assertEqual(self.run_().returncode, 0)
        for s in SUBJECTS:
            b = json.loads((self.pack / "refs" / f"{s}.png.blessed.json").read_text())
            self.assertEqual(b["sha256"], sha(self.pack / "refs" / f"{s}.png"))
            self.assertIn("Gary Sheng", b["blessedBy"])
            self.assertIn("2026-10-15", b["blessedBy"])
            self.assertIn("A · Ascent poster", b["note"])

    def test_the_pick_is_recorded_with_what_was_considered(self):
        self.assertEqual(self.run_().returncode, 0)
        pf = self.manifest()["promotedFrom"]
        self.assertEqual(pf["pick"], "A-ascent-poster")
        self.assertEqual(pf["considered"], list(DIRS), "sheets are not directions")
        self.assertEqual(pf["decided"], {"by": "Gary Sheng", "on": "2026-10-15",
                                         "verbatim": ["A · Ascent poster"]})
        self.assertEqual(set(pf["refs"]), {f"refs/{s}.png" for s in SUBJECTS})
        self.assertTrue(pf["refs"]["refs/diane.png"].endswith("diane/A-ascent-poster.png"))

    def test_scope_use_writes_a_typed_scope_the_engine_accepts(self):
        r = self.run_("--scope-use", "superskills-from-zero:reader-portraits",
                      "--scope-subjects", "the book's made-up readers",
                      "--scope-never", "a real person")
        self.assertEqual(r.returncode, 0, r.stderr)
        sc = self.manifest()["scope"]
        self.assertEqual(sc["uses"], ["superskills-from-zero:reader-portraits"])
        self.assertEqual(sc["never"], ["a real person"])
        self.assertEqual(sc["decided"]["by"], "Gary Sheng")
        sys.path.insert(0, str(ENGINE))
        from agenticstory.scope import scope_problems
        self.assertEqual(scope_problems(sc, "p"), [])

    def test_a_subject_without_the_pick_is_refused_by_name(self):
        (self.explore / "jordan" / "A-ascent-poster.png").unlink()
        r = self.run_()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("jordan", r.stderr)
        self.assertIn("B-ink-line-wash", r.stderr, "say what IS there")
        self.assertFalse((self.pack / "pack.json").exists())

    def test_an_unknown_pick_names_the_directions(self):
        r = self.run_("--pick", "Z-nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("A-ascent-poster", r.stderr)

    def test_a_pick_needs_who_decided(self):
        r = self.run_("--from-explore", str(self.explore), "--pick", "A-ascent-poster",
                      base=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--decided-by", r.stderr)

    def test_a_scope_needs_who_decided_and_their_words(self):
        r = self.run_("--anchor", str(self.explore / "diane" / "A-ascent-poster.png"),
                      "--ref", str(self.explore / "jordan" / "A-ascent-poster.png"),
                      "--ref", str(self.explore / "marcus" / "A-ascent-poster.png"),
                      "--scope-use", "x:y", base=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--decided-by", r.stderr)

    def test_one_flat_explore_dir_names_the_ref_for_the_pick(self):
        flat = self.explore / "diane"
        r = self.run_("--from-explore", str(flat), "--pick", "A-ascent-poster",
                      "--decided-by", "Gary Sheng", "--verbatim", "A",
                      "--ref", str(self.explore / "jordan" / "B-ink-line-wash.png"),
                      "--ref", str(self.explore / "marcus" / "B-ink-line-wash.png"), base=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        m = self.manifest()
        self.assertEqual(m["anchor"], "refs/A-ascent-poster.png")
        self.assertEqual(m["promotedFrom"]["decided"]["on"], datetime.date.today().isoformat())
        # only the picked ref is blessed by the pick; the extra refs are candidates
        self.assertTrue((self.pack / "refs" / "A-ascent-poster.png.blessed.json").exists())
        self.assertFalse((self.pack / "refs" / "B-ink-line-wash.png.blessed.json").exists())

    def test_without_from_explore_nothing_changes(self):
        a = self.explore / "diane" / "A-ascent-poster.png"
        r = self.run_("--anchor", str(a), "--ref", str(self.explore / "diane" / "B-ink-line-wash.png"),
                      "--ref", str(self.explore / "diane" / "C-warm-gouache.png"), base=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        m = self.manifest()
        self.assertNotIn("promotedFrom", m)
        self.assertNotIn("scope", m)


if __name__ == "__main__":
    unittest.main()
