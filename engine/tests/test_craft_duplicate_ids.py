"""Two craft-canon files with one id: `validate` names both (SPEC §13, v0.61).

The store keys craft records by id, so a second file carrying an id the first already used
replaced it in memory with no word said. Whichever sorted last was the record every reader saw.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agenticstory.store import CanonStore


def rule(**over):
    r = {"id": "brand-rule", "kind": "register-rule", "name": "A rule", "summary": "what it holds"}
    r.update(over)
    return r


class DuplicateCraftIdTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="abu-craft-dup-"))
        (self.dir / "canon" / "entities").mkdir(parents=True)
        self.craft = self.dir / "canon" / "craft"
        self.craft.mkdir(parents=True)
        (self.dir / "universe.json").write_text(json.dumps({"id": "t", "name": "T", "assetRoot": ".", "identity": {}}))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def put(self, name, rec):
        (self.craft / name).write_text(json.dumps(rec), encoding="utf-8")

    def craft_problems(self):
        return [p for p in CanonStore(self.dir).validate_canon() if p.startswith("craft id ")]

    def test_distinct_ids_are_no_problem(self):
        self.put("a.json", rule())
        self.put("b.json", rule(id="other-rule"))
        store = CanonStore(self.dir)
        self.assertEqual(store.craft_collisions, [])
        self.assertEqual(self.craft_problems(), [])

    def test_one_id_in_two_files_is_reported_with_both_filenames(self):
        self.put("a.json", rule(summary="the first"))
        self.put("b.json", rule(summary="the second"))
        store = CanonStore(self.dir)  # loading must not raise
        self.assertEqual(store.craft_collisions, [("brand-rule", "a.json", "b.json")])
        self.assertEqual(store.craft["brand-rule"].raw["summary"], "the second")  # last one wins, as before
        self.assertEqual(self.craft_problems(), [
            "craft id 'brand-rule' is declared by both a.json and b.json; one record would silently replace the other"])

    def test_it_holds_for_every_kind_including_two_kinds_sharing_an_id(self):
        self.put("a.json", rule(id="brand-kit"))
        self.put("b.json", {"id": "brand-kit", "kind": "kit", "name": "Kit", "summary": "s", "pieces": [], "noGos": []})
        got = "\n".join(self.craft_problems())
        self.assertIn("craft id 'brand-kit' is declared by both a.json and b.json", got)

    def test_three_files_name_every_file(self):
        for name in ("a.json", "b.json", "c.json"):
            self.put(name, rule())
        got = "\n".join(self.craft_problems())
        for name in ("a.json", "b.json", "c.json"):
            self.assertIn(name, got)

    def test_a_craft_record_is_read_as_utf8_whatever_the_locale(self):
        self.put("a.json", rule(summary="SPEC §13"))
        self.assertEqual(CanonStore(self.dir).craft["brand-rule"].raw["summary"], "SPEC §13")


if __name__ == "__main__":
    unittest.main()
