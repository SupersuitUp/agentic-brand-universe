"""Which surface a decision is shown on, and the honest degrade (SPEC v0.51).

The whole point of this module is that the two answers must not be interchangeable. A frapp
can serve the picture, so the record it produces is a fact; a text card cannot, so the record
it produces has to SAY it is about a filename. Every test here pins one half of that.

Nothing in this file starts a frapp, opens a browser or touches the network. The resolver is
the only thing under test, and it is a pure function of the environment.
"""
import pathlib
import tempfile
import unittest

from agenticstory import display


def _fake_freedom(root, versions=("4.9.0", "4.269.0")):
    """A cache dir shaped like a Freedom install, with the one file the resolver looks for."""
    for v in versions:
        lib = pathlib.Path(root) / v / ".agents" / "lib"
        lib.mkdir(parents=True, exist_ok=True)
        (lib / display.LIB_FILE).write_text("// not the real library, just its shape")
    return {"FREEDOM_CACHE_DIR": str(root)}


class WhereTheLibraryIs(unittest.TestCase):
    def test_the_newest_install_wins_and_it_is_not_a_string_sort(self):
        # 4.269.0 is newer than 4.9.0 and sorts before it as a string. A frapp resolved
        # against the wrong one imports a library the operator has already replaced.
        with tempfile.TemporaryDirectory() as root:
            env = _fake_freedom(root)
            self.assertEqual(display.freedom_lib(env=env).parts[-4], "4.269.0")

    def test_no_install_is_none_rather_than_a_guess(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(display.freedom_lib(env={"FREEDOM_CACHE_DIR": root}))

    def test_a_dev_checkout_overrides_the_cache(self):
        # The maintainer's own machine runs the library from a checkout, and a frapp that
        # ignored it would test the shipped copy rather than the change being made.
        with tempfile.TemporaryDirectory() as root:
            lib = pathlib.Path(root) / "lib"
            lib.mkdir()
            (lib / display.LIB_FILE).write_text("// dev")
            self.assertEqual(display.freedom_lib(env={display.ENV_LIB: str(lib)}).parent, lib)


class TheSupersuitCache(unittest.TestCase):
    """Freedom became Supersuit on 2026-10-14 and its plugin cache moved from
    freedom-workspace/freedom to supersuit/supersuit. With only the old root known, every
    board on a Supersuit machine reported "no Freedom install" and degraded to a text card
    (2026-11-23, the works board for the orb-free wiki heroes)."""

    def test_the_supersuit_root_is_found_when_the_old_freedom_root_is_absent(self):
        import os
        from unittest import mock
        with tempfile.TemporaryDirectory() as new, tempfile.TemporaryDirectory() as old:
            _fake_freedom(new, versions=("8.9.0",))
            env = {k: v for k, v in os.environ.items() if k != "FREEDOM_CACHE_DIR"}
            with mock.patch.object(display, "FREEDOM_CACHE_ROOTS", (new, old)):
                self.assertEqual(display.freedom_lib(env=env).parts[-4], "8.9.0")

    def test_one_shared_list_names_supersuit_first_and_every_board_reads_it(self):
        import json
        roots = json.loads((pathlib.Path(display.__file__).with_name(
            "freedom_cache_roots.json")).read_text())["roots"]
        self.assertTrue(roots[0].endswith("cache/supersuit/supersuit"))
        self.assertEqual(tuple(roots), display.FREEDOM_CACHE_ROOTS)
        repo = pathlib.Path(display.__file__).resolve().parents[2]
        for f in ("skills/approve-works/frapps/works-board.mjs",
                  "skills/approve-works/frapps/mount.mjs",
                  "skills/shoot-references/frapps/shot-board.mjs"):
            src = (repo / f).read_text()
            self.assertIn("freedom_cache_roots.json", src, f)
            self.assertNotIn('"freedom-workspace", "freedom"', src, f)
        src = (repo / "skills/approve-works/frapps/mount.mjs").read_text()
        mount = src[src.index("const hostLib"):src.index("if (!hostLib")]
        # The store's host library and CLI were renamed with the product; mounting a works
        # board on a Supersuit machine needs the new names, newest first.
        self.assertLess(mount.index("supersuit-tile-app-host.mjs"), mount.index("freedom-frapp-host.mjs"))
        self.assertLess(mount.index("create-or-manage-a-supertool/scripts/host.mjs"),
                        mount.index("create-or-manage-frapp/scripts/host.mjs"))


class WhichChannel(unittest.TestCase):
    def test_a_freedom_install_and_node_give_the_frapp(self):
        with tempfile.TemporaryDirectory() as root:
            env = _fake_freedom(root)
            env["ABU_NODE"] = "/bin/sh"          # any real binary: node's presence is the test
            self.assertEqual(display.resolve_channel(env=env), (display.FRAPP, ""))

    def test_no_freedom_install_degrades_to_the_card_and_says_why(self):
        """THE TEST THAT FAILS WITHOUT THE FIX: a machine that cannot show the art must not
        produce the same answer as one that can."""
        with tempfile.TemporaryDirectory() as root:
            channel, why = display.resolve_channel(
                env={"FREEDOM_CACHE_DIR": root, "ABU_NODE": "/bin/sh"})
            self.assertEqual(channel, display.CARD)
            self.assertIn("no Freedom install", why)
            # It must say what the card cannot do, or the record carries a shrug.
            self.assertIn("cannot carry the picture", why)

    def test_no_node_degrades_to_the_card_because_a_frapp_is_a_node_program(self):
        with tempfile.TemporaryDirectory() as root:
            env = _fake_freedom(root)
            env["ABU_NODE"] = str(pathlib.Path(root) / "no-such-node")
            channel, why = display.resolve_channel(env=env)
            self.assertEqual(channel, display.CARD)
            self.assertIn("no `node`", why)

    def test_the_channel_can_be_forced_to_the_card_and_the_record_names_the_force(self):
        # A test suite and a headless run both need this, and it is not an off switch: an
        # approval taken on the card channel is recorded as unshown whatever set it.
        with tempfile.TemporaryDirectory() as root:
            env = _fake_freedom(root)
            env.update({"ABU_NODE": "/bin/sh", "ABU_DISPLAY_CHANNEL": "card"})
            channel, why = display.resolve_channel(env=env)
            self.assertEqual(channel, display.CARD)
            self.assertIn("ABU_DISPLAY_CHANNEL=card", why)


class ThePendingRecord(unittest.TestCase):
    def test_a_pending_record_is_never_already_served(self):
        # Only the page that sends the bytes may flip this, which is the reason the whole
        # mechanism is not another attestation.
        self.assertFalse(display.pending(display.FRAPP)["served"])
        self.assertFalse(display.pending(display.CARD, "no install")["served"])

    def test_the_card_record_carries_its_reason_and_the_frapp_record_has_none_to_carry(self):
        self.assertEqual(display.pending(display.CARD, "no install")["why"], "no install")
        self.assertNotIn("why", display.pending(display.FRAPP))

    def test_an_unknown_channel_is_refused(self):
        with self.assertRaises(ValueError):
            display.pending("preview")


if __name__ == "__main__":
    unittest.main()
