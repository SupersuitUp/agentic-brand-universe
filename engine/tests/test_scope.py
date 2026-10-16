"""A Style Pack's typed `scope` and a register's typed medium exception (SPEC v0.62, issue #60).

Earned 2026-10-15 on continental-works. Gary picked an illustrated look for the made-up readers
of one book, inside a universe whose register is film photography and rejects illustration. The
pick could only be recorded as prose: a free-form `scope` string on the pack and an `exceptions`
note on a craft record. Nothing could read either, so the pack would have rendered for ANY
subject on ANY surface, and the register's refusal of illustration was quietly untrue. These
tests hold both to a shape `validate` and `generate.py` can read.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agenticstory import scope as S
from agenticstory.store import CanonStore

DECIDED = {"by": "Gary Sheng", "on": "2026-10-15",
           "verbatim": ["Illustrated, in the CW look", "A · Ascent poster"]}
USE = "superskills-from-zero:reader-portraits"
SCOPE = {"uses": [USE], "subjects": "the book's made-up readers", "never": ["a real person"],
         "decided": DECIDED}
EXC = {"id": "reader-portraits", "medium": "flat 1970s screen-print illustration",
       "stylePack": "reference/style/ascent-poster", "uses": [USE], "decided": DECIDED,
       "why": "a photograph of a made-up person would pass for a real one"}


class ScopeShape(unittest.TestCase):
    def test_a_sound_scope_has_no_problems(self):
        self.assertEqual(S.scope_problems(SCOPE, "p"), [])

    def test_prose_scope_is_refused_and_says_how_to_type_it(self):
        got = "\n".join(S.scope_problems("ONLY the made-up readers", "p"))
        self.assertIn("prose", got)
        self.assertIn("uses", got)

    def test_every_missing_field_is_named(self):
        got = "\n".join(S.scope_problems({"uses": [], "decided": {"on": "15 Oct"}}, "p"))
        for word in ("uses", "decided.by", "decided.on", "decided.verbatim"):
            self.assertIn(word, got)

    def test_verbatim_may_be_one_string(self):
        sc = dict(SCOPE, decided=dict(DECIDED, verbatim="A"))
        self.assertEqual(S.scope_problems(sc, "p"), [])


class UniverseCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="abu-scope-"))
        (self.dir / "canon" / "entities").mkdir(parents=True)
        self.pack = self.dir / "reference" / "style" / "ascent-poster"
        (self.pack / "refs").mkdir(parents=True)
        (self.pack / "refs" / "a.png").write_bytes(b"\x89PNG")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, pack_scope=SCOPE, exceptions=(EXC,), register=None):
        pk = {"id": "ascent-poster", "anchor": "refs/a.png", "refs": ["refs/a.png"],
              "gate": ["g"], "styleLine": "s", "textPolicy": "none"}
        if pack_scope is not None:
            pk["scope"] = pack_scope
        (self.pack / "pack.json").write_text(json.dumps(pk))
        reg = register if register is not None else {
            "name": "film photography", "anchor": None,
            "rejectedPoles": ["illustration, painting, drawing"],
            "exceptions": list(exceptions)}
        (self.dir / "universe.json").write_text(json.dumps(
            {"id": "t", "name": "T", "assetRoot": ".", "identity": {"register": reg}}))

    def problems(self):
        return [p for p in CanonStore(self.dir).validate_canon()
                if "scope" in p or "exceptions" in p]


class ValidateReadsBoth(UniverseCase):
    def test_sound_pack_and_exception_validate(self):
        self.write()
        self.assertEqual(self.problems(), [])

    def test_a_prose_pack_scope_fails_validate(self):
        self.write(pack_scope="ONLY the made-up readers")
        self.assertTrue(any("ascent-poster" in p and "prose" in p for p in self.problems()))

    def test_an_exception_needs_who_when_and_words(self):
        bad = dict(EXC, decided={"by": "Gary Sheng"})
        self.write(exceptions=[bad])
        got = "\n".join(self.problems())
        self.assertIn("decided.on", got)
        self.assertIn("decided.verbatim", got)

    def test_an_exception_needs_a_medium_and_uses(self):
        bad = {k: v for k, v in EXC.items() if k not in ("medium", "uses")}
        self.write(exceptions=[bad])
        got = "\n".join(self.problems())
        self.assertIn("medium", got)
        self.assertIn("uses", got)

    def test_an_exception_pack_must_exist(self):
        self.write(exceptions=[dict(EXC, stylePack="reference/style/gone")])
        self.assertTrue(any("gone" in p for p in self.problems()))

    def test_the_pack_must_carry_a_typed_scope_covering_the_exception(self):
        self.write(pack_scope=None)
        self.assertTrue(any("no typed scope" in p for p in self.problems()))
        self.write(pack_scope=dict(SCOPE, uses=["some-other-use"]))
        self.assertTrue(any(USE in p for p in self.problems()))

    def test_duplicate_exception_ids_are_refused(self):
        self.write(exceptions=[EXC, EXC])
        self.assertTrue(any("twice" in p for p in self.problems()))

    def test_a_string_register_or_no_exceptions_is_untouched(self):
        self.write(register="photoreal", pack_scope=None)
        self.assertEqual(self.problems(), [])


class TheRenderGate(UniverseCase):
    """`use_gate(pack, pack_dir, use)` is what generate.py calls before spending a render."""

    def gate(self, use):
        pk = json.loads((self.pack / "pack.json").read_text())
        return S.use_gate(pk, self.pack, use)

    def test_a_scoped_pack_refuses_a_render_with_no_use(self):
        self.write()
        problem, _ = self.gate(None)
        self.assertIn("--use", problem)
        self.assertIn(USE, problem)

    def test_a_scoped_pack_refuses_a_use_outside_its_scope(self):
        self.write()
        problem, _ = self.gate("homepage:hero")
        self.assertIn("homepage:hero", problem)
        self.assertIn(USE, problem)

    def test_an_in_scope_use_passes_and_names_the_exception(self):
        self.write()
        problem, rec = self.gate(USE)
        self.assertIsNone(problem)
        self.assertEqual(rec["use"], USE)
        self.assertEqual(rec["registerException"]["id"], "reader-portraits")
        self.assertEqual(rec["registerException"]["decided"]["by"], "Gary Sheng")

    def test_a_prose_scope_refuses_at_render_time_too(self):
        self.write(pack_scope="ONLY the made-up readers")
        problem, _ = self.gate(USE)
        self.assertIn("prose", problem)

    def test_an_exception_alone_also_gates_the_use(self):
        """A register exception names the pack; a use outside it is refused even if the pack
        has no scope of its own (validate also flags that pack)."""
        self.write(pack_scope=None)
        self.assertIsNotNone(self.gate("homepage:hero")[0])
        self.assertIsNone(self.gate(USE)[0])

    def test_an_unscoped_pack_outside_any_exception_is_free(self):
        self.write(pack_scope=None, exceptions=[])
        problem, rec = self.gate(None)
        self.assertIsNone(problem)
        self.assertEqual(rec, {})
        self.assertEqual(self.gate("anything")[1], {"use": "anything"})

    def test_a_standalone_pack_with_no_universe_still_gates_on_its_scope(self):
        lone = Path(tempfile.mkdtemp(prefix="abu-lone-"))
        try:
            pk = {"id": "x", "scope": SCOPE}
            self.assertIsNotNone(S.use_gate(pk, lone, None)[0])
            self.assertIsNone(S.use_gate(pk, lone, USE)[0])
        finally:
            shutil.rmtree(lone, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
