"""`abu report`: anyone running ABU can file what it got wrong, with enough context that the
maintainers can act on it without a follow-up question. Earned 2026-10-14, Gary: "it should be
easy to suggest changes for anything that we ship to people", and "it is very very important that
really good context gets put into the issues".

The command never sends anything. It prints (and with --open, opens) a pre-filled new-issue page;
the person reads it and presses submit.
"""
import io
import unittest
from contextlib import redirect_stdout
from urllib.parse import parse_qs, urlparse

from agenticstory.cli import main
from agenticstory.report import MAX_URL, REPO, issue_url, environment


def _parse(url):
    u = urlparse(url)
    return u, {k: v[0] for k, v in parse_qs(u.query).items()}


class ReportTest(unittest.TestCase):
    def test_report_prints_a_prefilled_issue_on_the_abu_repo(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["report", "check-kit refused the iOS blue in our iMessage simulator"]), 0)
        url = [l for l in out.getvalue().split("\n") if l.startswith("https://")][0]
        u, q = _parse(url)
        self.assertEqual(u.netloc, "github.com")
        self.assertEqual(u.path, f"/{REPO}/issues/new")
        self.assertIn("iOS blue", q["title"])
        for want in ("check-kit refused the iOS blue", "What I expected", "Steps or command",
                     "ABU version", "Python", "OS"):
            self.assertIn(want, q["body"])
        self.assertIn("nothing is sent", out.getvalue().lower(), "the reporter is told they still press submit")

    def test_context_flags_land_in_the_body(self):
        with redirect_stdout(io.StringIO()) as out:
            main(["report", "shoot-references locked a defect", "--expected", "the read-back gate refuses it",
                  "--command", "abu lock-shot u chip front", "--skill", "abu:shoot-references"])
        _, q = _parse([l for l in out.getvalue().split("\n") if l.startswith("https://")][0])
        for want in ("the read-back gate refuses it", "abu lock-shot u chip front", "abu:shoot-references"):
            self.assertIn(want, q["body"])

    def test_environment_names_a_real_version(self):
        env = environment()
        self.assertRegex(env["abu"], r"^\d+\.\d+\.\d+$")
        self.assertNotEqual(env["abu"], "0.0.1", "the stale package __version__ is not the release")

    def test_a_long_body_is_trimmed_to_a_url_github_accepts_and_says_so(self):
        url = issue_url("t", "x" * 50000)
        self.assertLessEqual(len(url), MAX_URL)
        self.assertIn("trimmed", _parse(url)[1]["body"].lower())


if __name__ == "__main__":
    unittest.main()
