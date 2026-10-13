"""Golden lines (SPEC §13.2, v0.61): a universe's approved language as a validated record.

Earned 2026-10-13. A two-person company had no record of its approved wording and nothing that
knew which page carried which sentence, so every copy drifted on its own.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import agenticstory
from agenticstory import lines as L
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
        self.assertIn("instead names 'nope', which is not a golden or retired line", self.joined(record(line(), dict(old, instead="nope"))))
        self.assertIn("instead names itself", self.joined(record(line(), dict(old, instead="old-one"))))

    def test_ids_are_kebab_case_and_unique(self):
        self.assertIn("id must be kebab-case", self.joined(record(line(id="What It Is"))))
        self.assertIn("id is already used", self.joined(record(line(), line(text="Different words here."))))

    def test_one_wording_is_one_line(self):
        twin = line(id="twin", text="The suit you build out of software you own.")
        self.assertIn("has the same text as line 'what-it-is'", self.joined(record(line(), twin)))
        retired = dict(twin, status="retired", instead="what-it-is")
        self.assertEqual(self.problems(record(line(), retired)), [])

    def test_wrong_types_are_reported_not_raised(self):
        for bad in (["a"], {"k": 1}):
            old = line(id="old-one", text="An older sentence entirely.", status="retired", instead=bad)
            got = self.joined(record(line(), old))
            self.assertIn("instead must be the id of a golden or retired line, or null", got)
        got = self.joined(record(line(version=2, history=[{"version": True, "text": "The suit you build.",
                                                          "replacedOn": "2026-10-13", "replacedBy": "Ada Reyes"}])))
        self.assertIn("history must hold versions 1 to 1 once each", got)
        self.assertIn("history must be a list", self.joined(record(line(history={}))))
        self.assertIn("history must be a list", self.joined(record(line(history=""))))

    def retired(self, lid, instead, **over):
        return line(id=lid, name=lid, text=f"The {lid} sentence, no longer said.", status="retired",
                    instead=instead, **over)

    def test_instead_may_name_a_retired_line_and_never_a_candidate(self):
        # a -> b -> what-it-is: b was retired after a named it, and a still says where to go.
        chain = record(line(), self.retired("a", "b"), self.retired("b", "what-it-is"))
        self.assertEqual(self.problems(chain), [])
        # A chain may also end at a retired line that nothing replaces.
        end = dict(self.retired("b", None), insteadNote="we stopped saying this")
        self.assertEqual(self.problems(record(line(), self.retired("a", "b"), end)), [])
        cand = line(id="maybe", text="A sentence nobody has approved.", status="candidate"); cand.pop("decided")
        got = self.joined(record(line(), cand, self.retired("a", "maybe")))
        self.assertIn("line 'a': instead names 'maybe', which is not a golden or retired line", got)

    def test_an_instead_chain_that_loops_is_reported_not_followed_forever(self):
        two = self.problems(record(line(), self.retired("a", "b"), self.retired("b", "a")))
        self.assertEqual([p for p in two if "loops" in p],
                         ["lines brand-lines line 'a': instead chain loops: a -> b -> a"])
        three = self.problems(record(line(), self.retired("a", "b"), self.retired("b", "c"), self.retired("c", "a")))
        self.assertEqual([p for p in three if "loops" in p],
                         ["lines brand-lines line 'a': instead chain loops: a -> b -> c -> a"])
        # A line that only LEADS INTO a loop is not a second loop, and the walk still ends.
        tail = self.problems(record(line(), self.retired("z", "b"), self.retired("b", "c"), self.retired("c", "b")))
        self.assertEqual([p for p in tail if "loops" in p],
                         ["lines brand-lines line 'b': instead chain loops: b -> c -> b"])
        # Naming itself keeps its own message and is not reported twice.
        own = self.problems(record(line(), self.retired("a", "a")))
        self.assertEqual(own, ["lines brand-lines line 'a': instead names itself"])

    def test_a_date_is_a_real_calendar_date(self):
        for bad in ("2026-99-99", "2026-02-30"):
            got = self.joined(record(line(decided=dict(DECIDED, on=bad))))
            self.assertIn(f"decided.on must be a YYYY-MM-DD date, got {bad!r}", got)
            hist = [{"version": 1, "text": "The suit you build.", "replacedOn": bad, "replacedBy": "Ada Reyes"}]
            got = self.joined(record(line(version=2, history=hist)))
            self.assertIn(f"history v1 replacedOn must be a YYYY-MM-DD date, got {bad!r}", got)
        self.assertEqual(self.problems(record(line(decided=dict(DECIDED, on="2028-02-29")))), [])

    def test_a_record_whose_lines_are_the_wrong_shape_is_reported_not_raised(self):
        for bad in (5, "a line", {"id": "x"}):
            self.assertIn("needs a 'lines' list", self.joined(record(lines=bad)))
        self.assertIn("line #1 must be an object", self.joined(record(line(), "a bare sentence")))
        l = line(); l["decided"] = dict(DECIDED); l["decided"].pop("by")
        self.assertIn("decided.by is missing", self.joined(record(l)))
        got = self.joined(record(line(version=2, history=["The suit you build."])))
        self.assertIn("each history entry is {version, text, replacedOn, replacedBy}", got)
        got = self.joined(record(line(version=2, history=[{"version": 1}])))
        self.assertIn("history v1 has no text", got)

    def test_norm_compares_wording_only(self):
        self.assertEqual(norm("The “suit” you\n  build, out of *software* you [own](https://x.y/z)."),
                         'The "suit" you build, out of software you own.')
        self.assertNotEqual(norm("the suit"), norm("The suit"))


class ListVerbTest(LinesBase):
    def run_cli(self, *argv):
        with redirect_stdout(io.StringIO()) as out:
            code = main(list(argv))
        return code, out.getvalue()

    def test_it_lists_every_line_with_its_status_and_version(self):
        cand = line(id="maybe", text="A sentence nobody has approved.", status="candidate"); cand.pop("decided")
        self.file.write_text(json.dumps(record(line(), cand)))
        code, out = self.run_cli("lines", str(self.dir))
        self.assertEqual(code, 0)
        self.assertIn("lines brand-lines: Lines", out)
        self.assertIn("approvers: Ada Reyes, Ben Okafor", out)
        self.assertRegex(out, r"golden\s+what-it-is\s+v1\s+\[public, client\]")
        self.assertRegex(out, r"candidate\s+maybe\s+v1")
        self.assertIn("The suit you build out of software you own.", out)

    def test_status_filters_and_json_is_the_lines(self):
        cand = line(id="maybe", text="A sentence nobody has approved.", status="candidate"); cand.pop("decided")
        self.file.write_text(json.dumps(record(line(), cand)))
        code, out = self.run_cli("lines", str(self.dir), "--status", "golden", "--json")
        self.assertEqual(code, 0)
        self.assertEqual([l["id"] for l in json.loads(out)], ["what-it-is"])

    def test_a_universe_with_no_record_says_so(self):
        code, out = self.run_cli("lines", str(self.dir))
        self.assertEqual(code, 0)
        self.assertIn("no lines: this universe records no golden lines (SPEC §13.2)", out)
        code, out = self.run_cli("lines", str(self.dir), "--json")
        self.assertEqual(json.loads(out), [])


    def test_approvers_of_the_wrong_type_are_reported_and_still_listed(self):
        for bad in ([1, "Ada Reyes"], "Ada Reyes", 7, {"a": 1}):
            self.file.write_text(json.dumps(record(approvers=bad)))
            self.assertIn("'approvers' must list at least one person",
                          "\n".join(CanonStore(self.dir).validate_canon()))
            code, out = self.run_cli("lines", str(self.dir))
            self.assertEqual(code, 0)
            self.assertIn("lines brand-lines: Lines", out)
            self.assertIn("what-it-is", out)
        self.file.write_text(json.dumps(record(approvers=[1, "Ada Reyes"])))
        self.assertIn("approvers: 1, Ada Reyes", self.run_cli("lines", str(self.dir))[1])

    def test_lines_and_audiences_of_the_wrong_type_never_raise(self):
        self.file.write_text(json.dumps(record(line(audiences=[3, "public"]), "a bare sentence")))
        code, out = self.run_cli("lines", str(self.dir))
        self.assertEqual(code, 0)
        self.assertIn("[3, public]", out)
        self.file.write_text(json.dumps(record(lines=5)))
        self.assertEqual(self.run_cli("lines", str(self.dir))[0], 0)
        code, out = self.run_cli("lines", str(self.dir), "--json")
        self.assertEqual((code, json.loads(out)), (0, []))


    def test_a_shadowed_record_is_said_out_loud_in_the_listing(self):
        # Hand-made: two files, one id. The listing can only show the one the store kept, so it
        # says which, where before it showed the later file's approvers as if they were the record's.
        self.file.write_text(json.dumps(record()))
        (self.dir / "canon" / "craft" / "zz-agent.json").write_text(json.dumps(record(approvers=["An Agent"])))
        code, out = self.run_cli("lines", str(self.dir))
        self.assertEqual(code, 0)
        self.assertIn("approvers: An Agent", out)
        self.assertIn("NOTE: craft id 'brand-lines' is declared by both brand-lines.json and zz-agent.json; "
                      "this listing shows zz-agent.json, and `abu validate` refuses the universe until one is removed", out)
        err = io.StringIO()
        with mock.patch("sys.stderr", err):
            code, out = self.run_cli("lines", str(self.dir), "--json")
        self.assertEqual([l["id"] for l in json.loads(out)], ["what-it-is"])  # stdout stays JSON
        self.assertIn("NOTE: craft id 'brand-lines'", err.getvalue())
        (self.dir / "canon" / "craft" / "zz-agent.json").unlink()
        self.assertNotIn("NOTE", self.run_cli("lines", str(self.dir))[1])


class WriterVerbTest(LinesBase):
    YES = ["--by", "Ada Reyes", "--on", "2026-10-13", "--verbatim", "yes, that is the one"]

    def run_cli(self, *argv):
        with redirect_stdout(io.StringIO()) as out:
            code = main(list(argv))
        return code, out.getvalue()

    def lines(self):
        return {l["id"]: l for l in json.loads(self.file.read_text())["lines"]}

    def add(self, *extra):
        return self.run_cli("line-add", str(self.dir), "--id", "what-it-is", "--name", "What it is",
                            "--for", "the answer when someone asks", "--text", "The suit you build.",
                            "--audience", "public,client", *extra)

    def test_the_first_add_needs_approvers_and_then_creates_the_record(self):
        code, out = self.add()
        self.assertEqual(code, 1)
        self.assertIn("--approver", out)
        self.assertFalse(self.file.exists())
        code, out = self.add("--approver", "Ada Reyes", "--approver", "Ben Okafor")
        self.assertEqual(code, 0)
        rec = json.loads(self.file.read_text())
        self.assertEqual((rec["kind"], rec["approvers"]), ("lines", ["Ada Reyes", "Ben Okafor"]))
        l = self.lines()["what-it-is"]
        self.assertEqual((l["status"], l["version"], l["audiences"]), ("candidate", 1, ["public", "client"]))
        self.assertNotIn("decided", l)
        self.assertEqual([p for p in CanonStore(self.dir).validate_canon() if p.startswith("lines ")], [])

    def test_add_with_a_yes_is_golden_and_bless_makes_a_candidate_golden(self):
        self.add("--approver", "Ada Reyes", *self.YES)
        self.assertEqual(self.lines()["what-it-is"]["status"], "golden")
        self.run_cli("line-add", str(self.dir), "--id", "two", "--name", "Two", "--for", "f",
                     "--text", "Another sentence.", "--audience", "team")
        code, _ = self.run_cli("line-bless", str(self.dir), "two", *self.YES)
        self.assertEqual(code, 0)
        self.assertEqual(self.lines()["two"]["decided"]["verbatim"], "yes, that is the one")

    def test_a_yes_from_a_non_approver_changes_nothing(self):
        self.add("--approver", "Ada Reyes")
        before = self.file.read_bytes()
        code, out = self.run_cli("line-bless", str(self.dir), "what-it-is",
                                 "--by", "An Agent", "--on", "2026-10-13", "--verbatim", "looks right")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)
        self.assertIn("not one of this record's approvers", out)
        self.assertEqual(self.file.read_bytes(), before)

    def test_reword_keeps_the_old_wording_and_bumps_the_version(self):
        self.add("--approver", "Ada Reyes", *self.YES)
        code, out = self.run_cli("line-reword", str(self.dir), "what-it-is", "--text", "The suit you build out of software you own.",
                                 "--by", "Ada Reyes", "--on", "2026-10-20", "--verbatim", "say software you own")
        self.assertEqual(code, 0)
        self.assertIn("v1 -> v2", out)
        l = self.lines()["what-it-is"]
        self.assertEqual(l["version"], 2)
        self.assertEqual(l["text"], "The suit you build out of software you own.")
        self.assertEqual(l["history"], [{"version": 1, "text": "The suit you build.",
                                         "replacedOn": "2026-10-20", "replacedBy": "Ada Reyes"}])
        self.assertEqual(l["decided"]["verbatim"], "say software you own")
        self.assertEqual([p for p in CanonStore(self.dir).validate_canon() if p.startswith("lines ")], [])

    def test_rewording_a_golden_line_needs_a_yes_and_new_words(self):
        self.add("--approver", "Ada Reyes", *self.YES)
        before = self.file.read_bytes()
        code, out = self.run_cli("line-reword", str(self.dir), "what-it-is", "--text", "Something else.")
        self.assertEqual(code, 1)
        self.assertIn("needs --by and --verbatim", out)
        code, out = self.run_cli("line-reword", str(self.dir), "what-it-is", "--text", "The  suit you *build*.", *self.YES)
        self.assertEqual(code, 1)
        self.assertIn("same wording", out)
        self.assertEqual(self.file.read_bytes(), before)

    def test_rewording_a_candidate_is_free_and_keeps_no_history(self):
        self.add("--approver", "Ada Reyes")
        code, _ = self.run_cli("line-reword", str(self.dir), "what-it-is", "--text", "A better draft.")
        self.assertEqual(code, 0)
        l = self.lines()["what-it-is"]
        self.assertEqual((l["version"], l["text"], l.get("history")), (1, "A better draft.", None))

    def test_retire_names_a_replacement_or_a_reason(self):
        self.add("--approver", "Ada Reyes", *self.YES)
        self.run_cli("line-add", str(self.dir), "--id", "old", "--name", "Old", "--for", "f",
                     "--text", "An older sentence.", "--audience", "public", *self.YES)
        code, out = self.run_cli("line-retire", str(self.dir), "old", *self.YES)
        self.assertEqual(code, 1)
        self.assertIn("--instead", out)
        code, _ = self.run_cli("line-retire", str(self.dir), "old", *self.YES, "--instead", "what-it-is")
        self.assertEqual(code, 0)
        self.assertEqual((self.lines()["old"]["status"], self.lines()["old"]["instead"]), ("retired", "what-it-is"))

    def test_unknown_ids_and_duplicates_are_refused(self):
        self.add("--approver", "Ada Reyes")
        code, out = self.run_cli("line-bless", str(self.dir), "nope", *self.YES)
        self.assertEqual(code, 1)
        self.assertIn("no line 'nope'", out)
        code, out = self.add()
        self.assertEqual(code, 1)
        self.assertIn("already has a line 'what-it-is'", out)


    def refused(self, code, out):
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)

    def test_the_record_must_live_where_validation_reads(self):
        for rec in ("other.json", "../outside.json", "canon/craft/../../sneaky.json"):
            code, out = self.add("--approver", "Ada Reyes", "--record", rec)
            self.refused(code, out)
            self.assertIn("canon/craft", out)
        for rel in ("other.json", "sneaky.json"):
            self.assertFalse((self.dir / rel).exists())
        self.assertFalse((self.dir.parent / "outside.json").exists())

    def test_a_broken_record_file_is_refused_not_raised(self):
        for content in ("{bad", "[]"):
            self.file.write_text(content)
            code, out = self.add("--approver", "Ada Reyes")
            self.refused(code, out)
            self.assertEqual(self.file.read_text(), content)

    def test_a_write_that_raises_is_rolled_back(self):
        self.add("--approver", "Ada Reyes")
        before = self.file.read_bytes()
        rec = json.loads(before)
        rec["lines"][0]["text"] = "Changed in memory only."
        with mock.patch("agenticstory.lines.validate_lines", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                L.write(self.dir, self.file, rec)
            self.assertEqual(self.file.read_bytes(), before)
            fresh = self.dir / "canon" / "craft" / "fresh.json"
            with self.assertRaises(RuntimeError):
                L.write(self.dir, fresh, rec)
            self.assertFalse(fresh.exists())

    def test_retire_refuses_both_a_replacement_and_a_note(self):
        self.add("--approver", "Ada Reyes", *self.YES)
        self.run_cli("line-add", str(self.dir), "--id", "other", "--name", "Other", "--for", "f",
                     "--text", "Another sentence.", "--audience", "public", *self.YES)
        before = self.file.read_bytes()
        code, out = self.run_cli("line-retire", str(self.dir), "what-it-is", *self.YES,
                                 "--instead", "other", "--note", "we stopped saying this")
        self.refused(code, out)
        self.assertEqual(self.file.read_bytes(), before)

    def test_retire_with_a_note_and_no_replacement(self):
        self.add("--approver", "Ada Reyes", *self.YES)
        code, _ = self.run_cli("line-retire", str(self.dir), "what-it-is", *self.YES, "--note", "we stopped saying this")
        self.assertEqual(code, 0)
        l = self.lines()["what-it-is"]
        self.assertEqual((l["status"], l["instead"], l["insteadNote"]), ("retired", None, "we stopped saying this"))

    def test_an_unknown_audience_is_refused_and_nothing_is_created(self):
        code, out = self.run_cli("line-add", str(self.dir), "--id", "x", "--name", "X", "--for", "f",
                                 "--text", "A sentence.", "--audience", "public,investor", "--approver", "Ada Reyes")
        self.refused(code, out)
        self.assertFalse(self.file.exists())

    # --- one record, chosen by the universe and never minted by a verb (C1, I1) ---

    def craft(self, name):
        return self.dir / "canon" / "craft" / name

    def craft_files(self):
        return sorted(f.name for f in (self.dir / "canon" / "craft").iterdir())

    def put(self, name, rec):
        self.craft(name).write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")

    def ada_universe(self):
        """A universe whose approved record holds one golden line, said yes to by Ada."""
        code, _ = self.run_cli("line-add", str(self.dir), "--id", "a", "--name", "A", "--for", "f",
                               "--text", "Alpha line.", "--audience", "public",
                               "--approver", "Ada Reyes", "--by", "Ada Reyes", "--verbatim", "yes")
        self.assertEqual(code, 0)
        return self.file.read_bytes()

    def agent_add(self, *extra):
        return self.run_cli("line-add", str(self.dir), "--id", "b", "--name", "B", "--for", "f",
                            "--text", "Agent line.", "--audience", "public", *extra)

    def still_adas(self, before):
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.craft_files(), ["brand-lines.json"])
        code, out = self.run_cli("lines", str(self.dir))
        self.assertIn("approvers: Ada Reyes", out)
        self.assertNotIn("An Agent", out)
        self.assertRegex(out, r"golden\s+a\s+v1")
        self.assertEqual(CanonStore(self.dir).validate_canon(), [])

    def test_a_new_record_takes_its_id_from_its_file(self):
        self.assertEqual(L.new_record(["Ada Reyes"])["id"], "brand-lines")
        self.assertEqual(L.new_record(["Ada Reyes"], id="our-lines")["id"], "our-lines")
        self.ada_universe()
        self.assertEqual(json.loads(self.file.read_text())["id"], "brand-lines")

    def test_a_second_file_cannot_shadow_the_approved_record(self):
        # The reviewer's sequence: a later-sorting file reusing the id replaced Ada's approvers.
        before = self.ada_universe()
        code, out = self.agent_add("--record", "canon/craft/zz-agent.json", "--approver", "An Agent",
                                   "--by", "An Agent", "--verbatim", "I like it")
        self.refused(code, out)
        self.assertIn("--record selects an existing lines record; canon/craft/zz-agent.json is not one", out)
        self.assertIn("never a second one", out)
        self.still_adas(before)

    def test_a_first_sorting_file_cannot_take_unvalidated_writes(self):
        # The mirror: aa.json sorted first, the store never saw it, and every write said "added".
        before = self.ada_universe()
        for extra in (["--approver", "An Agent"],
                      ["--audience", "bogus", "--by", "Nobody", "--on", "never", "--verbatim", "v"]):
            code, out = self.agent_add("--record", "canon/craft/aa.json", *extra)
            self.refused(code, out)
            self.assertNotIn("added", out)
            self.still_adas(before)

    def test_write_reports_success_only_for_the_record_the_universe_loaded(self):
        before = self.ada_universe()
        rec = json.loads(before)
        # Hand-made: a second file with the same id, sorting later, so the store loads IT.
        self.put("zz.json", dict(rec, approvers=["An Agent"], lines=[]))
        rec["lines"][0]["name"] = "Changed"
        got = L.write(self.dir, self.file, rec)
        self.assertIn("lines brand-lines: brand-lines.json is not the record the universe loaded for this id "
                      "(another file declares the same id)", got)
        self.assertEqual(self.file.read_bytes(), before)
        # And sorting FIRST, where the store does load this file but a second one still claims the id.
        self.craft("zz.json").unlink()
        self.put("aa.json", dict(rec, approvers=["An Agent"], lines=[]))
        self.assertTrue(any("is not the record the universe loaded" in p for p in L.write(self.dir, self.file, rec)))
        self.assertEqual(self.file.read_bytes(), before)

    def test_a_first_record_whose_id_another_craft_file_holds_is_not_created(self):
        self.put("a-rule.json", {"id": "brand-lines", "kind": "register-rule", "name": "R", "summary": "s"})
        code, out = self.add("--approver", "Ada Reyes")
        self.refused(code, out)
        self.assertIn("is not the record the universe loaded for this id", out)
        self.assertEqual(self.craft_files(), ["a-rule.json"])

    def ours(self, *lines_):
        self.put("our-lines.json", {"id": "our-lines", "kind": "lines", "name": "Ours", "summary": "s",
                                    "approvers": ["Ada Reyes"], "lines": list(lines_)})
        return self.craft("our-lines.json").read_bytes()

    def test_the_one_record_is_used_whatever_its_filename(self):
        self.ours()
        code, out = self.add(*self.YES)
        self.assertEqual(code, 0)
        self.assertIn("canon/craft/our-lines.json", out)
        self.assertEqual(self.craft_files(), ["our-lines.json"])
        rec = json.loads(self.craft("our-lines.json").read_text())
        self.assertEqual((rec["id"], rec["approvers"], rec["lines"][0]["status"]), ("our-lines", ["Ada Reyes"], "golden"))
        code, out = self.run_cli("line-reword", str(self.dir), "what-it-is", "--text", "The suit you own.", *self.YES)
        self.assertEqual(code, 0)
        self.assertIn("canon/craft/our-lines.json", out)
        self.assertEqual(CanonStore(self.dir).validate_canon(), [])

    def test_a_verb_never_mints_a_second_record_with_its_own_approvers(self):
        # The reviewer's sequence: with --approver the verb made brand-lines.json beside our-lines.json.
        before = self.ours()
        code, out = self.add("--approver", "An Agent", "--by", "An Agent", "--verbatim", "y")
        self.refused(code, out)
        self.assertIn("this universe already has a lines record; its approvers are Ada Reyes. Who can approve "
                      "is changed by the operator in the record file, never by a verb.", out)
        self.assertEqual(self.craft_files(), ["our-lines.json"])
        self.assertEqual(self.craft("our-lines.json").read_bytes(), before)
        # Naming a listed approver is refused too: it is never silently ignored.
        code, out = self.add("--approver", "Ada Reyes")
        self.refused(code, out)
        self.assertEqual(self.craft("our-lines.json").read_bytes(), before)

    def test_record_selects_an_existing_lines_record_and_nothing_else(self):
        before = self.ours()
        self.put("a-rule.json", {"id": "a-rule", "kind": "register-rule", "name": "R", "summary": "s"})
        rule = self.craft("a-rule.json").read_bytes()
        for rec in ("canon/craft/brand-lines.json", "canon/craft/new.json", "canon/craft/a-rule.json"):
            code, out = self.add("--record", rec, *self.YES)
            self.refused(code, out)
            self.assertIn(f"--record selects an existing lines record; {rec} is not one. A verb creates the "
                          "universe's first lines record at canon/craft/brand-lines.json and never a second one.", out)
        self.assertEqual(self.craft_files(), ["a-rule.json", "our-lines.json"])
        self.assertEqual((self.craft("our-lines.json").read_bytes(), self.craft("a-rule.json").read_bytes()), (before, rule))
        code, out = self.add("--record", "canon/craft/our-lines.json", *self.YES)
        self.assertEqual(code, 0)
        # On an empty universe --record cannot choose where the first record goes.
        self.craft("our-lines.json").unlink()
        code, out = self.add("--record", "canon/craft/mine.json", "--approver", "Ada Reyes")
        self.refused(code, out)
        self.assertFalse(self.craft("mine.json").exists())

    def test_two_records_need_record_to_say_which(self):
        self.ours()
        self.put("their-lines.json", {"id": "their-lines", "kind": "lines", "name": "Theirs", "summary": "s",
                                      "approvers": ["Ben Okafor"], "lines": []})
        before = {n: self.craft(n).read_bytes() for n in self.craft_files()}
        code, out = self.add(*self.YES)
        self.refused(code, out)
        self.assertIn("canon/craft/our-lines.json", out)
        self.assertIn("canon/craft/their-lines.json", out)
        self.assertIn("--record", out)
        # Each record keeps its own approvers: Ada's yes is no yes in Ben's record.
        code, out = self.add("--record", "canon/craft/their-lines.json", *self.YES)
        self.refused(code, out)
        self.assertIn("not one of this record's approvers (Ben Okafor)", out)
        self.assertEqual({n: self.craft(n).read_bytes() for n in self.craft_files()}, before)
        code, out = self.add("--record", "canon/craft/our-lines.json", *self.YES)
        self.assertEqual(code, 0)
        self.assertEqual(self.craft("their-lines.json").read_bytes(), before["their-lines.json"])
        code, out = self.run_cli("line-bless", str(self.dir), "what-it-is", *self.YES)
        self.refused(code, out)
        self.assertIn("--record", out)

    def test_a_record_whose_lines_are_not_a_list_is_refused_not_raised(self):
        for bad in (5, None, {"id": "x"}):
            self.put("brand-lines.json", record(lines=bad))
            before = self.file.read_bytes()
            for argv in (("line-add", str(self.dir), "--id", "x", "--name", "X", "--for", "f", "--text", "T.", "--audience", "public"),
                         ("line-bless", str(self.dir), "x", *self.YES)):
                code, out = self.run_cli(*argv)
                self.refused(code, out)
                self.assertIn("'lines' is not a list", out)
            self.assertEqual(self.file.read_bytes(), before)

    # --- a write lands whole or not at all (I2) ---

    def test_a_write_that_cannot_land_leaves_the_record_as_it_was(self):
        before = self.ada_universe()
        with mock.patch("agenticstory.lines.os.replace", side_effect=OSError("disk said no")):
            code, out = self.agent_add()
        self.refused(code, out)
        self.assertIn("nothing was written", out)
        self.assertIn("disk said no", out)
        self.assertNotIn("would not load", out)
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.craft_files(), ["brand-lines.json"])  # no temp file left behind
        # And a FIRST write that cannot land leaves no file at all, never an empty one.
        self.file.unlink()
        with mock.patch("agenticstory.lines.os.replace", side_effect=OSError("disk said no")):
            code, out = self.add("--approver", "Ada Reyes")
        self.refused(code, out)
        self.assertEqual(self.craft_files(), [])

    def test_a_failure_while_writing_the_bytes_leaves_no_temp_file(self):
        before = self.ada_universe()
        with mock.patch("agenticstory.lines.json.dumps", return_value="\udcff"):  # cannot be encoded as UTF-8
            code, out = self.agent_add()
        self.refused(code, out)
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.craft_files(), ["brand-lines.json"])

    def c_locale(self, *argv):
        engine = str(Path(agenticstory.__file__).resolve().parent.parent)
        env = dict(os.environ, LC_ALL="C", PYTHONCOERCECLOCALE="0", PYTHONUTF8="0", PYTHONPATH=engine)
        env.pop("LANG", None); env.pop("PYTHONIOENCODING", None)
        return subprocess.run([sys.executable, "-m", "agenticstory.cli", *argv], env=env, capture_output=True)

    def test_the_first_line_is_written_as_utf8_whatever_the_locale(self):
        got = self.c_locale("line-add", str(self.dir), "--id", "a", "--name", "A", "--for", "f",
                            "--text", "Alpha line.", "--audience", "public", "--approver", "Ada Reyes")
        self.assertEqual(got.returncode, 0, got.stdout + got.stderr)
        self.assertIn(b"added candidate line 'a'", got.stdout)
        rec = json.loads(self.file.read_bytes().decode("utf-8"))
        self.assertIn("§13.2", rec["summary"])
        self.assertEqual(CanonStore(self.dir).validate_canon(), [])
        # And the record it wrote is read back the same way for the second line.
        got = self.c_locale("line-add", str(self.dir), "--id", "b", "--name", "B", "--for", "f",
                            "--text", "Beta line.", "--audience", "public")
        self.assertEqual(got.returncode, 0, got.stdout + got.stderr)
        self.assertEqual(sorted(self.lines()), ["a", "b"])

    def test_a_record_that_is_not_utf8_says_so_and_is_never_called_invalid_json(self):
        self.file.write_bytes('{"id": "brand-lines", "kind": "lines", "name": "caf\xe9"}'.encode("latin-1"))
        before = self.file.read_bytes()
        code, out = self.add("--approver", "Ada Reyes")
        self.refused(code, out)
        self.assertIn("canon/craft/brand-lines.json could not be read as UTF-8", out)
        self.assertNotIn("not valid JSON", out)
        self.assertNotIn("remove", out)
        self.assertEqual(self.file.read_bytes(), before)

    # --- retiring down a chain (I3) ---

    def test_a_line_another_retired_line_points_at_can_itself_be_retired(self):
        self.add("--approver", "Ada Reyes", *self.YES)
        for lid, text in (("b", "Beta line."), ("c", "Gamma line."), ("d", "Delta line.")):
            self.run_cli("line-add", str(self.dir), "--id", lid, "--name", lid, "--for", "f",
                         "--text", text, "--audience", "public", *self.YES)
        retire = lambda lid, *how: self.run_cli("line-retire", str(self.dir), lid, *self.YES, *how)
        self.assertEqual(retire("what-it-is", "--instead", "b")[0], 0)
        code, out = retire("b", "--instead", "c")          # the reviewer's dead end
        self.assertEqual(code, 0, out)
        self.assertEqual(retire("c", "--note", "we stopped saying any of this")[0], 0)
        got = self.lines()
        self.assertEqual([(got[i]["status"], got[i]["instead"]) for i in ("what-it-is", "b", "c")],
                         [("retired", "b"), ("retired", "c"), ("retired", None)])
        self.assertEqual(CanonStore(self.dir).validate_canon(), [])
        # A verb cannot close the chain into a loop.
        before = self.file.read_bytes()
        code, out = retire("d", "--instead", "d")
        self.refused(code, out)
        self.assertIn("instead names itself", out)
        self.assertEqual(self.file.read_bytes(), before)

    def test_retiring_toward_a_candidate_or_a_missing_line_is_refused(self):
        self.add("--approver", "Ada Reyes", *self.YES)
        self.run_cli("line-add", str(self.dir), "--id", "maybe", "--name", "Maybe", "--for", "f",
                     "--text", "A draft.", "--audience", "public")
        before = self.file.read_bytes()
        for target in ("maybe", "nope"):
            code, out = self.run_cli("line-retire", str(self.dir), "what-it-is", *self.YES, "--instead", target)
            self.refused(code, out)
            self.assertIn(f"instead names '{target}', which is not a golden or retired line", out)
        self.assertEqual(self.file.read_bytes(), before)

    # --- the yes (minors 1 to 3) ---

    def test_an_empty_by_or_verbatim_is_no_yes(self):
        self.add("--approver", "Ada Reyes")
        self.run_cli("line-add", str(self.dir), "--id", "g", "--name", "G", "--for", "f",
                     "--text", "A golden sentence.", "--audience", "public", *self.YES)
        before = self.file.read_bytes()
        for by, verbatim in (("", ""), ("Ada Reyes", ""), ("", "yes"), ("Ada Reyes", "   "), ("  ", "yes")):
            yes = ("--by", by, "--verbatim", verbatim)
            for argv in (("line-bless", str(self.dir), "what-it-is", *yes),
                         ("line-retire", str(self.dir), "g", *yes, "--note", "we stopped"),
                         ("line-reword", str(self.dir), "g", "--text", "Another golden sentence.", *yes),
                         ("line-add", str(self.dir), "--id", "n", "--name", "N", "--for", "f", "--text", "New.",
                          "--audience", "public", *yes)):
                code, out = self.run_cli(*argv)
                self.refused(code, out)
                self.assertIn("a yes is --by AND --verbatim", out)
        self.assertEqual(self.file.read_bytes(), before)

    def test_a_yes_given_while_rewording_a_candidate_is_refused_not_dropped(self):
        self.add("--approver", "Ada Reyes")
        before = self.file.read_bytes()
        code, out = self.run_cli("line-reword", str(self.dir), "what-it-is", "--text", "A better draft.", *self.YES)
        self.refused(code, out)
        self.assertIn("line 'what-it-is' is a candidate: reword it without a yes, then make it golden with line-bless", out)
        self.assertEqual(self.file.read_bytes(), before)

    def test_an_impossible_date_is_refused_by_every_verb_that_takes_one(self):
        self.add("--approver", "Ada Reyes")
        self.run_cli("line-add", str(self.dir), "--id", "g", "--name", "G", "--for", "f",
                     "--text", "A golden sentence.", "--audience", "public", *self.YES)
        before = self.file.read_bytes()
        for bad in ("2026-99-99", "2026-02-30"):
            yes = ("--by", "Ada Reyes", "--verbatim", "yes", "--on", bad)
            code, out = self.run_cli("line-bless", str(self.dir), "what-it-is", *yes)
            self.refused(code, out)
            self.assertIn(f"decided.on must be a YYYY-MM-DD date, got {bad!r}", out)
            code, out = self.run_cli("line-reword", str(self.dir), "g", "--text", "Another golden sentence.", *yes)
            self.refused(code, out)
            self.assertIn(f"history v1 replacedOn must be a YYYY-MM-DD date, got {bad!r}", out)
        self.assertEqual(self.file.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
