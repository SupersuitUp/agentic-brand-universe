"""The docs generator, and the staleness gate that is the actual point of it."""
import unittest
from pathlib import Path

from agenticstory import docsfile, SPEC_VERSION

ROOT = docsfile.repo_root()


class TestSources(unittest.TestCase):
    def test_repo_root_is_the_framework(self):
        self.assertTrue((ROOT / "SPEC.md").is_file())
        self.assertTrue((ROOT / "skills").is_dir())

    def test_spec_version_parses_and_matches_engine(self):
        version, date = docsfile.spec_version(ROOT)
        self.assertRegex(version, r"^\d+\.\d+$")
        self.assertRegex(date, r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(version, SPEC_VERSION)

    def test_changelog_entries_found(self):
        entries = docsfile.spec_changelog(ROOT)
        self.assertGreater(len(entries), 3)
        for e in entries:
            self.assertRegex(e["version"], r"^\d+\.\d+$")
            self.assertTrue(e["headline"])
            self.assertNotIn("\n", e["headline"])

    def test_every_skill_has_name_and_description(self):
        """A skill whose frontmatter cannot be read is invisible to an agent
        choosing a verb, which is the failure this index exists to prevent."""
        missing = []
        for d in sorted((ROOT / "skills").iterdir()):
            f = d / "SKILL.md"
            if not f.is_file():
                continue
            fm = docsfile.frontmatter(f)
            if not fm.get("name") or not fm.get("description"):
                missing.append(d.name)
        self.assertEqual(missing, [])

    def test_skill_id_matches_directory(self):
        for d in sorted((ROOT / "skills").iterdir()):
            f = d / "SKILL.md"
            if f.is_file():
                self.assertEqual(docsfile.frontmatter(f).get("name"), d.name)

    def test_every_agent_has_name_and_description(self):
        """Same rule as skills: frontmatter that cannot be read makes the surface
        invisible to whoever is choosing what to dispatch."""
        bad = [a["id"] for a in docsfile.agents(ROOT) if not a["id"] or not a["summary"]]
        self.assertEqual(bad, [])

    def test_agent_id_matches_filename(self):
        for p in docsfile._md_dir(ROOT, "agents"):
            self.assertEqual(docsfile.frontmatter(p).get("name"), p.stem)

    def test_every_command_has_a_description(self):
        blank = [c["id"] for c in docsfile.commands(ROOT) if not c["summary"]]
        self.assertEqual(blank, [])

    def test_command_id_is_the_invocation_as_typed(self):
        """The row answers "what do I type", so it carries the plugin namespace."""
        for c in docsfile.commands(ROOT):
            self.assertRegex(c["id"], r"^/[a-z0-9-]+:[a-z0-9-]+$")

    def test_underscore_files_are_includes_not_surfaces(self):
        """`_conventions.md` is shared prose every command pulls from, not a command."""
        for name in ("agents", "commands"):
            for p in docsfile._md_dir(ROOT, name):
                self.assertFalse(p.name.startswith("_"))

    def test_surface_dirs_enumerate_rather_than_name(self):
        """The regression this generator was taught to prevent: abu-steward shipped
        for two months in no generated table because only `skills/` was enumerated.
        Every *.md dropped in these directories must become a row with no code change,
        so the count tracks the directory rather than a hand-kept list."""
        for name, source in (("agents", docsfile.agents), ("commands", docsfile.commands)):
            self.assertEqual(len(source(ROOT)), len(docsfile._md_dir(ROOT, name)))

    def test_steward_is_documented(self):
        """It is reachable three ways now; each one is a row somewhere."""
        self.assertIn("abu-steward", [a["id"] for a in docsfile.agents(ROOT)])
        self.assertIn("/abu:steward", [c["id"] for c in docsfile.commands(ROOT)])

    def test_marketplace_entry_is_projected_from_the_plugin_manifest(self):
        """The drift this projection was built to end: the marketplace copy was a
        whole paragraph behind plugin.json (the `make-a-work` entry)."""
        import json
        plugin = json.loads((ROOT / docsfile.PLUGIN).read_text())
        market = json.loads((ROOT / docsfile.MANIFEST).read_text())
        entry = next(p for p in market["plugins"] if p["name"] == plugin["name"])
        self.assertEqual(entry["description"], plugin["description"])

    def test_projection_leaves_the_marketplace_own_description_alone(self):
        """The top-level one is a browsing blurb, hand-written on purpose, and is not
        the skill catalog."""
        import json
        market = json.loads((ROOT / docsfile.MANIFEST).read_text())
        plugin = json.loads((ROOT / docsfile.PLUGIN).read_text())
        self.assertNotEqual(market["description"], plugin["description"])
        self.assertLess(len(market["description"]), 500)

    def test_projection_preserves_every_other_field(self):
        import json
        before = json.loads((ROOT / docsfile.MANIFEST).read_text())
        after = json.loads(docsfile.project_manifest(ROOT))
        self.assertEqual(set(before), set(after))
        self.assertEqual(before["owner"], after["owner"])
        self.assertEqual([p["source"] for p in before["plugins"]],
                         [p["source"] for p in after["plugins"]])

    def test_check_catches_manifest_drift(self):
        import json, shutil, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "*.png", "*.jpg", "*.webp", "*.mp3"))
            p = root / docsfile.MANIFEST
            d = json.loads(p.read_text())
            d["plugins"][0]["description"] = "stale copy"
            p.write_text(json.dumps(d, indent=2) + "\n")
            self.assertTrue(any("has drifted" in x for x in docsfile.check(root)))
            docsfile.build(root)
            self.assertFalse(any("has drifted" in x for x in docsfile.check(root)))

    def test_every_cli_verb_has_help(self):
        """A blank help string renders as a blank documentation row, which is how
        an undocumented verb hides in plain sight."""
        blank = [v["verb"] for v in docsfile.cli_verbs() if not v["help"]]
        self.assertEqual(blank, [])

    def test_static_test_count_is_plausible(self):
        counts = docsfile.test_counts(ROOT)
        self.assertGreater(counts["tests"], 100)
        self.assertGreater(counts["files"], 5)

    def test_first_sentence_does_not_truncate_on_abbreviations(self):
        text = "Scaffold a Style Pack (SPEC §4.7) — a portable folder. And more prose after it."
        self.assertTrue(docsfile.first_sentence(text).startswith("Scaffold a Style Pack"))
        self.assertNotIn("And more prose", docsfile.first_sentence(text))

    def test_first_sentence_rejoins_short_fragments(self):
        self.assertEqual(docsfile.first_sentence("Do it. Then the longer explanation follows here."),
                         "Do it. Then the longer explanation follows here.")


class TestRendering(unittest.TestCase):
    def test_tables_have_header_and_separator(self):
        for render in (docsfile.render_status, docsfile.render_skills, docsfile.render_cli,
                       docsfile.render_forms, docsfile.render_providers,
                       docsfile.render_spec_changelog):
            rows = render(ROOT)
            self.assertTrue(rows[0].startswith("|"), render.__name__)
            self.assertRegex(rows[1], r"^\|(-{3}\|)+$", render.__name__)

    def test_pipes_in_content_are_escaped(self):
        """An unescaped pipe from a skill description silently shatters the table."""
        for row in docsfile.render_skills(ROOT)[2:]:
            self.assertEqual(row.count("|") - row.count("\\|"), 4, row[:80])

    def test_replace_block_is_idempotent(self):
        text = "before\n<!-- BEGIN GENERATED: x -->\nold\n<!-- END GENERATED: x -->\nafter\n"
        once = docsfile._replace_block(text, "x", ["new"])
        self.assertIn("new", once)
        self.assertNotIn("old", once)
        self.assertEqual(once, docsfile._replace_block(once, "x", ["new"]))
        self.assertTrue(once.startswith("before"))
        self.assertTrue(once.endswith("after\n"))

    def test_replace_block_refuses_missing_markers(self):
        with self.assertRaises(ValueError):
            docsfile._replace_block("no markers here", "x", ["new"])


class TestGate(unittest.TestCase):
    def test_docs_are_current(self):
        """THE test. If this fails, run `abu build-docs` and commit the result.

        It is the whole reason this module exists: a generated doc that nobody is
        forced to regenerate rots exactly like the hand-written one it replaced."""
        self.assertEqual(docsfile.check(ROOT), [])

    def test_build_is_idempotent(self):
        """A second build with no source change must be a no-op, or `--check` would
        report stale forever and the gate would be noise."""
        self.assertEqual(docsfile.build(ROOT, write=False), [])

    def test_check_catches_a_stale_block(self):
        text = (ROOT / "docs" / "REFERENCE.md").read_text()
        tampered = docsfile._replace_block(text, "cli", ["| Verb | What it does |", "|---|---|"])
        self.assertNotEqual(tampered, text)

    def test_check_catches_spec_version_drift(self):
        """The one invariant prose cannot hold: two files bumped by hand, in lockstep."""
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "repo"
            fake.mkdir()
            (fake / "SPEC.md").write_text("# Spec\n\n**v9.99 — 2026-01-01.** nope\n")
            for rel in ("README.md", "docs/REFERENCE.md"):
                (fake / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, fake / rel)
            shutil.copytree(ROOT / "skills", fake / "skills")
            problems = docsfile.check(fake)
            self.assertTrue(any("spec version mismatch" in p for p in problems), problems)


class TestReportBlock(unittest.TestCase):
    """Every skill ends by offering to report a misfire (2026-10-14).

    The report step shipped in the front door and the steward only, so a skill that
    misfired mid-chain, where misfires actually happen, never offered it. The paragraph
    is GENERATED into every SKILL.md rather than pasted, so a new skill gets it from
    `abu build-docs` and a skill without it fails the gate."""

    def _fake_root(self, tmp, skill_text, spec=False):
        fake = Path(tmp) / "repo"
        (fake / "skills" / "demo").mkdir(parents=True)
        if spec:
            (fake / "SPEC.md").write_text(f"# Spec\n\n**v{SPEC_VERSION} — 2026-01-01.** x\n")
        (fake / "skills" / "demo" / "SKILL.md").write_text(skill_text)
        return fake

    def test_every_skill_carries_the_report_block_naming_itself(self):
        missing = []
        for d in sorted((ROOT / "skills").iterdir()):
            f = d / "SKILL.md"
            if not f.is_file():
                continue
            text = f.read_text()
            if docsfile.begin("report") not in text or f"--skill abu:{d.name}" not in text:
                missing.append(d.name)
        self.assertEqual(missing, [])

    def test_check_refuses_a_skill_without_the_block(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake = self._fake_root(tmp, "---\nname: demo\ndescription: d\n---\n\nBody.\n", spec=True)
            problems = docsfile.check(fake)
            self.assertTrue(any("skills/demo/SKILL.md" in p for p in problems), problems)

    def test_build_appends_the_block_once(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake = self._fake_root(tmp, "---\nname: demo\ndescription: d\n---\n\nBody.\n")
            docsfile.build(fake)
            text = (fake / "skills" / "demo" / "SKILL.md").read_text()
            self.assertTrue(text.startswith("---\nname: demo"))
            self.assertIn("Body.", text)
            self.assertEqual(text.count(docsfile.begin("report")), 1)
            self.assertIn("--skill abu:demo", text)
            docsfile.build(fake)
            self.assertEqual((fake / "skills" / "demo" / "SKILL.md").read_text(), text)
            (fake / "SPEC.md").write_text(f"# Spec\n\n**v{SPEC_VERSION} — 2026-01-01.** x\n")
            self.assertNotIn("skills/demo/SKILL.md", " ".join(docsfile.check(fake)))


class TestRunningAbuBlock(unittest.TestCase):
    """A skill that says `abu <verb>` also says what to do when `abu` is not on PATH
    (2026-10-27).

    `abu` is the npm package's bin. A Claude plugin install puts no `abu` on PATH, so
    `abu kit <universe>` in add-piece-or-no-go answered "command not found" and the agent
    went hunting through the plugin cache for bin/abu.mjs by hand. One skill of 43 carried
    a hand-written fallback, and that one `cd`-ed into engine/, which resolves a relative
    universe path inside the plugin. So the fallback is GENERATED, from one source, into
    every skill whose own prose invokes a real CLI verb."""

    def _fake_root(self, tmp, body):
        fake = Path(tmp) / "repo"
        (fake / "skills" / "demo").mkdir(parents=True)
        (fake / "skills" / "demo" / "SKILL.md").write_text(
            "---\nname: demo\ndescription: d\n---\n\n# Demo\n\nIntro.\n\n## Method\n\n" + body)
        return fake

    def test_detects_a_real_verb_and_ignores_prose(self):
        self.assertTrue(docsfile.invokes_abu("Run `abu kit <universe>` first."))
        self.assertTrue(docsfile.invokes_abu("then abu validate it"))
        self.assertFalse(docsfile.invokes_abu("Use `abu:shoot-references` next."))
        self.assertFalse(docsfile.invokes_abu("the abu framework is young"))

    def test_report_fence_alone_does_not_count_as_invoking(self):
        text = "Body.\n\n" + docsfile.begin("report") + "\n    abu report x\n" + docsfile.end("report") + "\n"
        self.assertFalse(docsfile.invokes_abu(docsfile.strip_generated(text)))

    def test_every_skill_invoking_abu_carries_the_block(self):
        missing = []
        for rel in docsfile.skill_files(ROOT):
            text = (ROOT / rel).read_text()
            if docsfile.invokes_abu(docsfile.strip_generated(text)) and docsfile.begin("running-abu") not in text:
                missing.append(rel)
        self.assertEqual(missing, [])

    def test_block_names_the_node_entrypoint_and_never_cds_into_engine(self):
        body = "\n".join(docsfile.render_running_abu())
        self.assertIn('bin/abu.mjs" <verb>', body)
        self.assertIn("CLAUDE_PLUGIN_ROOT", body)
        self.assertNotIn('cd "$ABU/engine"', body)

    def test_no_skill_keeps_a_hand_written_cd_engine_fallback(self):
        offenders = [rel for rel in docsfile.skill_files(ROOT)
                     if 'cd "$ABU/engine" && python3 -m agenticstory.cli' in (ROOT / rel).read_text()]
        self.assertEqual(offenders, [])

    def test_report_block_carries_the_fallback_too(self):
        self.assertIn("bin/abu.mjs", "\n".join(docsfile.render_report("demo")))

    def _check(self, fake):
        """check() needs SPEC.md for the version; build() would try to regenerate its
        fences, so it exists only while checking (the TestReportBlock pattern)."""
        spec = fake / "SPEC.md"
        spec.write_text(f"# Spec\n\n**v{SPEC_VERSION} — 2026-01-01.** x\n")
        try:
            return docsfile.check(fake)
        finally:
            spec.unlink()

    def test_check_refuses_and_build_inserts_before_the_first_section(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake = self._fake_root(tmp, "Run `abu validate <universe>`.\n")
            self.assertTrue(any("running-abu" in p for p in self._check(fake)))
            docsfile.build(fake)
            text = (fake / "skills" / "demo" / "SKILL.md").read_text()
            self.assertEqual(text.count(docsfile.begin("running-abu")), 1)
            self.assertLess(text.index(docsfile.begin("running-abu")), text.index("## Method"))
            self.assertGreater(text.index(docsfile.begin("running-abu")), text.index("Intro."))
            docsfile.build(fake)
            self.assertEqual((fake / "skills" / "demo" / "SKILL.md").read_text(), text)
            self.assertNotIn("skills/demo/SKILL.md", " ".join(self._check(fake)))

    def test_a_skill_that_never_invokes_abu_gets_no_block(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake = self._fake_root(tmp, "Look at the picture.\n")
            docsfile.build(fake)
            self.assertNotIn(docsfile.begin("running-abu"), (fake / "skills" / "demo" / "SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()
