"""A recipe published on the open web carries no home-folder or temporary-folder path (SPEC 3.2.1).

Earned 2026-11-23: supersuit.wiki served 96 `/Users/<name>/...` paths in one hero's recipe, and
compose-strip's export would have added dead `/private/tmp/<worktree>/...` ones.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agenticstory import public_paths as pp

ENGINE = Path(__file__).resolve().parents[1]


class TheRule(unittest.TestCase):
    def test_home_folder_becomes_tilde(self):
        s = "pass /Users/someone/Documents/repo/reference/a.png first"
        self.assertEqual(pp.publicize_text(s), "pass ~/Documents/repo/reference/a.png first")
        self.assertEqual(pp.publicize_text("/home/someone/x"), "~/x")

    def test_a_named_root_becomes_its_repo(self):
        s = "/private/tmp/wt-heroes/works/x/p1.png"
        self.assertEqual(pp.publicize_text(s, {"/private/tmp/wt-heroes": "the-universe"}),
                         "the-universe/works/x/p1.png")
        # /tmp and /private/tmp are one place on macOS
        self.assertEqual(pp.publicize_text("/tmp/wt-heroes/a", {"/private/tmp/wt-heroes": "u"}), "u/a")

    def test_a_live_temp_checkout_resolves_to_its_repo(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as d:
            repo = Path(d) / "wt"
            (repo / "works").mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "remote", "add", "origin",
                            "git@github.com:Org/my-universe.git"], check=True)
            pp._git_label.cache_clear()
            out = pp.publicize_text(f"{repo}/works/p.png")
            self.assertEqual(out, "my-universe/works/p.png")

    def test_a_dead_temp_path_keeps_only_its_tail(self):
        self.assertEqual(pp.publicize_text("/private/tmp/gone-xyz-123/works/p.png"),
                         "<tmp>/gone-xyz-123/works/p.png")

    def test_every_string_anywhere_and_the_recipe_says_so(self):
        r = {"prompt": "x", "refs": [{"path": "/Users/a/r.png"}],
             "panelRecipes": {"p1": {"entities": [{"universe": "/private/tmp/gone-q/u"}]}}}
        out, n = pp.publicize_recipe(r, recorded_at="/Users/a/u/works/x.png.recipe.json")
        self.assertEqual(n, 2)
        self.assertFalse(pp.has_private_paths(out))
        self.assertEqual(out["publicPaths"]["rewritten"], 2)
        self.assertEqual(out["publicPaths"]["recordedAt"], "~/u/works/x.png.recipe.json")
        self.assertEqual(r["refs"][0]["path"], "/Users/a/r.png")  # the input is not mutated

    def test_idempotent(self):
        out, _ = pp.publicize_recipe({"a": "/Users/a/b"})
        again, n = pp.publicize_recipe(out)
        self.assertEqual(n, 0)
        self.assertEqual(again["a"], "~/b")


class TheCommand(unittest.TestCase):
    def test_check_then_rewrite_in_place_and_a_clean_file_is_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            dirty = Path(d) / "a.webp.recipe.json"
            clean = Path(d) / "b.webp.recipe.json"
            dirty.write_text(json.dumps({"refs": [{"path": "/Users/a/r.png"}]}, indent=2))
            clean.write_text('{"refs": []}\n')
            run = lambda *a: subprocess.run([sys.executable, "-m", "agenticstory.cli",
                                             "publicize-recipes", *a], cwd=ENGINE,
                                            capture_output=True, text=True)
            self.assertEqual(run("--check", str(dirty), str(clean)).returncode, 1)
            self.assertIn("/Users/", dirty.read_text())
            self.assertEqual(run(str(dirty), str(clean)).returncode, 0)
            self.assertNotIn("/Users/", dirty.read_text())
            self.assertIn("publicPaths", json.loads(dirty.read_text()))
            self.assertEqual(clean.read_text(), '{"refs": []}\n')
            self.assertEqual(run("--check", str(dirty)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
