"""Golden lines (SPEC §13.2, v0.61): a universe's approved language as a validated record.

Earned 2026-10-13. A two-person company had no record of its approved wording and nothing that
knew which page carried which sentence, so every copy drifted on its own.
"""
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from agenticstory.cli import main
from agenticstory.lines import norm
from agenticstory.store import CanonStore

DECIDED = {"by": "Ada Reyes", "on": "2026-10-13", "verbatim": "yes, that is the one"}


def line(**over):
    l = {
        "id": "what-it-is", "name": "What it is", "for": "the answer when someone asks what the product is",
        "status": "golden", "text": "The suit you build out of software you own.", "version": 1,
        "audiences": ["public", "client"], "decided": dict(DECIDED),
    }
    l.update(over)
    return l


def record(*lines, **over):
    r = {"id": "brand-lines", "kind": "lines", "name": "Lines", "summary": "the approved language",
         "approvers": ["Ada Reyes", "Ben Okafor"], "lines": list(lines) if lines else [line()]}
    r.update(over)
    return r


class LinesBase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="abu-lines-"))
        (self.dir / "canon" / "entities").mkdir(parents=True)
        (self.dir / "canon" / "craft").mkdir(parents=True)
        (self.dir / "universe.json").write_text(json.dumps({"id": "t", "name": "T", "assetRoot": ".", "identity": {}}))
        self.file = self.dir / "canon" / "craft" / "brand-lines.json"

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def problems(self, rec):
        self.file.write_text(json.dumps(rec))
        return [p for p in CanonStore(self.dir).validate_canon() if p.startswith("lines ")]

    def joined(self, rec):
        return "\n".join(self.problems(rec))


class ValidateTest(LinesBase):
    def test_a_sound_record_validates(self):
        self.assertEqual(self.problems(record()), [])

    def test_no_record_is_fine(self):
        self.assertEqual([p for p in CanonStore(self.dir).validate_canon() if p.startswith("lines ")], [])

    def test_the_kind_is_known_to_the_store(self):
        self.file.write_text(json.dumps(record()))
        self.assertFalse(any("unknown craft kind" in p for p in CanonStore(self.dir).validate_canon()))

    def test_a_record_needs_approvers(self):
        self.assertIn("'approvers' must list at least one person", self.joined(record(approvers=[])))

    def test_a_golden_line_needs_a_recorded_yes(self):
        l = line(); l.pop("decided")
        self.assertIn("'decided' is missing", self.joined(record(l)))
        got = self.joined(record(line(decided={"by": "Ada Reyes", "on": "Oct 13"})))
        self.assertIn("YYYY-MM-DD", got)
        self.assertIn("decided.verbatim is missing", got)

    def test_only_an_approver_can_make_a_line_golden(self):
        got = self.joined(record(line(decided={"by": "An Agent", "on": "2026-10-13", "verbatim": "looks good"})))
        self.assertIn("'An Agent' is not one of this record's approvers", got)

    def test_a_candidate_carries_no_decision_and_needs_none(self):
        l = line(status="candidate"); l.pop("decided")
        self.assertEqual(self.problems(record(l)), [])
        self.assertIn("a candidate carries no 'decided'", self.joined(record(line(status="candidate"))))

    def test_status_and_audiences_are_closed_sets(self):
        self.assertIn("status must be one of candidate, golden, retired", self.joined(record(line(status="approved"))))
        self.assertIn("audience 'investor' is not one of", self.joined(record(line(audiences=["public", "investor"]))))
        self.assertIn("'audiences' must name at least one", self.joined(record(line(audiences=[]))))

    def test_required_words_are_required(self):
        got = self.joined(record(line(name="", text=" ")))
        self.assertIn("'name' is missing", got)
        self.assertIn("'text' is missing", got)
        l = line(); l.pop("for")
        self.assertIn("'for' is missing", self.joined(record(l)))

    def test_version_and_history_must_agree(self):
        self.assertIn("version must be a whole number, 1 or more", self.joined(record(line(version=0))))
        self.assertIn("history must hold versions 1 to 2 once each", self.joined(record(line(version=3))))
        hist = [{"version": 1, "text": "The suit you build.", "replacedOn": "2026-10-13", "replacedBy": "Ada Reyes"}]
        self.assertEqual(self.problems(record(line(version=2, history=hist))), [])
        bad = [{"version": 1, "text": "The suit you build.", "replacedOn": "yesterday"}]
        got = self.joined(record(line(version=2, history=bad)))
        self.assertIn("history v1 replacedOn must be a YYYY-MM-DD date", got)
        self.assertIn("history v1 has no replacedBy", got)

    def test_a_version_is_a_change_of_words(self):
        hist = [{"version": 1, "text": "The suit you build out of  *software* you own.",
                 "replacedOn": "2026-10-13", "replacedBy": "Ada Reyes"}]
        self.assertIn("two consecutive versions have the same wording", self.joined(record(line(version=2, history=hist))))

    def test_a_retired_line_names_its_replacement_or_says_there_is_none(self):
        old = line(id="old-one", text="An older sentence entirely.", status="retired")
        self.assertIn("'instead' is missing", self.joined(record(line(), old)))
        self.assertIn("'insteadNote' must say why", self.joined(record(line(), dict(old, instead=None))))
        self.assertEqual(self.problems(record(line(), dict(old, instead=None, insteadNote="we stopped saying this"))), [])
        self.assertEqual(self.problems(record(line(), dict(old, instead="what-it-is"))), [])
        self.assertIn("instead names 'nope', which is not a golden line", self.joined(record(line(), dict(old, instead="nope"))))
        self.assertIn("instead names itself", self.joined(record(line(), dict(old, instead="old-one"))))

    def test_ids_are_kebab_case_and_unique(self):
        self.assertIn("id must be kebab-case", self.joined(record(line(id="What It Is"))))
        self.assertIn("id is already used", self.joined(record(line(), line(text="Different words here."))))

    def test_one_wording_is_one_line(self):
        twin = line(id="twin", text="The suit you build out of software you own.")
        self.assertIn("has the same text as line 'what-it-is'", self.joined(record(line(), twin)))
        retired = dict(twin, status="retired", instead="what-it-is")
        self.assertEqual(self.problems(record(line(), retired)), [])

    def test_norm_compares_wording_only(self):
        self.assertEqual(norm("The “suit” you\n  build, out of *software* you [own](https://x.y/z)."),
                         'The "suit" you build, out of software you own.')
        self.assertNotEqual(norm("the suit"), norm("The suit"))


if __name__ == "__main__":
    unittest.main()
