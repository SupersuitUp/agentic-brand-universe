"""A provider reads its key from the operator's credentials file when the environment lacks it.

Earned 2026-10-15 (issue #61). The first `abu:explore` render failed with no image because the
OpenAI key lived in ~/.agents/.env/credentials.env, the operator's sanctioned key file, and the
provider read only the environment. It worked once someone loaded the key by hand, which is the
toil this removes. Two refusals ride with it: the key is never printed, and a key missing from
BOTH places fails with a message naming the variable AND the file, so the operator knows where
to put it.

Stdlib only, no SDK, no network. The provider modules are importable without their SDKs because
both import openai / google-genai inside main().
"""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SHARED = HERE.parent
PROVIDERS = SHARED.parent
sys.path.insert(0, str(SHARED))

import credentials  # noqa: E402

SECRET = "sk-test-DO-NOT-PRINT-0123456789"


def load(provider):
    path = PROVIDERS / provider / "generate_image.py"
    spec = importlib.util.spec_from_file_location(f"prov_{provider.replace('-', '_')}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CredFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.file = self.dir / "credentials.env"

    def tearDown(self):
        self._tmp.cleanup()

    def env(self, **extra):
        """An environment with no provider keys, pointed at the temp credentials file."""
        e = {k: v for k, v in os.environ.items()
             if k not in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ABU_CREDENTIALS_FILE")}
        e["ABU_CREDENTIALS_FILE"] = str(self.file)
        e.update(extra)
        return e


class ReadsTheFile(CredFile):
    def test_env_missing_file_has_it(self):
        self.file.write_text(f"OTHER=1\nOPENAI_API_KEY={SECRET}\n")
        with mock.patch.dict(os.environ, self.env(), clear=True):
            value, source = credentials.resolve_key("OPENAI_API_KEY")
        self.assertEqual(value, SECRET)
        self.assertEqual(source, str(self.file))

    def test_the_environment_wins_over_the_file(self):
        self.file.write_text("OPENAI_API_KEY=from-file\n")
        with mock.patch.dict(os.environ, self.env(OPENAI_API_KEY="from-env"), clear=True):
            value, source = credentials.resolve_key("OPENAI_API_KEY")
        self.assertEqual((value, source), ("from-env", "environment"))

    def test_an_explicit_key_wins_over_both(self):
        self.file.write_text("OPENAI_API_KEY=from-file\n")
        with mock.patch.dict(os.environ, self.env(OPENAI_API_KEY="from-env"), clear=True):
            value, source = credentials.resolve_key("OPENAI_API_KEY", provided="flag")
        self.assertEqual((value, source), ("flag", "--api-key"))

    def test_export_prefix_quotes_comments_and_blank_lines(self):
        self.file.write_text(
            "# a comment\n\nexport GEMINI_API_KEY=\"g-quoted\"\n"
            "OPENAI_API_KEY='o-single'  \n")
        with mock.patch.dict(os.environ, self.env(), clear=True):
            self.assertEqual(credentials.resolve_key("GEMINI_API_KEY")[0], "g-quoted")
            self.assertEqual(credentials.resolve_key("OPENAI_API_KEY")[0], "o-single")

    def test_a_prefix_match_is_not_a_match(self):
        """OPENAI_API_KEY_OLD must never be read as OPENAI_API_KEY."""
        self.file.write_text("OPENAI_API_KEY_OLD=stale\n")
        with mock.patch.dict(os.environ, self.env(), clear=True):
            self.assertIsNone(credentials.resolve_key("OPENAI_API_KEY")[0])

    def test_an_empty_value_counts_as_missing(self):
        self.file.write_text("OPENAI_API_KEY=\n")
        with mock.patch.dict(os.environ, self.env(), clear=True):
            self.assertIsNone(credentials.resolve_key("OPENAI_API_KEY")[0])

    def test_no_file_is_not_an_error_by_itself(self):
        with mock.patch.dict(os.environ, self.env(), clear=True):
            self.assertEqual(credentials.resolve_key("OPENAI_API_KEY"), (None, None))

    def test_the_default_file_is_the_operators_sanctioned_one(self):
        e = self.env()
        e.pop("ABU_CREDENTIALS_FILE")
        with mock.patch.dict(os.environ, e, clear=True):
            self.assertEqual(credentials.credentials_file(),
                             Path("~/.agents/.env/credentials.env").expanduser())


class TheMissingMessage(CredFile):
    def test_names_the_variable_and_the_file(self):
        msg = credentials.missing_message("OPENAI_API_KEY")
        self.assertIn("OPENAI_API_KEY", msg)
        with mock.patch.dict(os.environ, self.env(), clear=True):
            msg = credentials.missing_message("OPENAI_API_KEY")
        self.assertIn(str(self.file), msg)
        self.assertIn("environment", msg)


class EachProviderUsesIt(CredFile):
    """The shared reader is only worth anything if BOTH providers call it."""

    def _get(self, provider, *args):
        mod = load(provider)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                return mod.get_api_key(*args), out.getvalue() + err.getvalue(), None
            except SystemExit as e:
                return None, out.getvalue() + err.getvalue(), e

    def test_gpt_reads_the_file_and_never_prints_the_key(self):
        self.file.write_text(f"OPENAI_API_KEY={SECRET}\n")
        with mock.patch.dict(os.environ, self.env(), clear=True):
            key, printed, exited = self._get("gpt-image-2", None)
        self.assertIsNone(exited)
        self.assertEqual(key, SECRET)
        self.assertNotIn(SECRET, printed)
        self.assertNotIn(SECRET[-6:], printed)

    def test_nano_reads_the_file_and_never_prints_the_key(self):
        self.file.write_text(f"GEMINI_API_KEY={SECRET}\n")
        with mock.patch.dict(os.environ, self.env(), clear=True):
            key, printed, exited = self._get("nano-banana-pro", None)
        self.assertIsNone(exited)
        self.assertEqual(key, SECRET)
        self.assertNotIn(SECRET, printed)

    def test_gpt_missing_in_both_fails_naming_variable_and_file(self):
        with mock.patch.dict(os.environ, self.env(), clear=True):
            key, printed, exited = self._get("gpt-image-2", None)
        self.assertIsNotNone(exited, "a missing key must exit, not render with None")
        self.assertNotEqual(exited.code, 0)
        self.assertIn("OPENAI_API_KEY", printed)
        self.assertIn(str(self.file), printed)

    def test_nano_missing_in_both_fails_naming_variable_and_file(self):
        with mock.patch.dict(os.environ, self.env(), clear=True):
            key, printed, exited = self._get("nano-banana-pro", None)
        self.assertIsNotNone(exited)
        self.assertIn("GEMINI_API_KEY", printed)
        self.assertIn(str(self.file), printed)


if __name__ == "__main__":
    unittest.main()
