"""`abu check-share` (Gary, 2026-10-16: "Update the guard to worry more than tech specs", then "put this
at the most general level possible because people are always making websites if they're having an
agentic brand universe"). Earned on continentalworks.ai/supersuit/computer, which shipped wearing
/supersuit's share card, a plinth and "By introduction only", while every unfurl check passed: they
all measure the card, and none asks whether it is THIS page's card.

What is asserted is the part no size check sees: a new page with no card of its own, a new page
wearing another page's card, and that only what a push ADDS is judged.
"""
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from agenticstory.cli import main
from agenticstory.share import cards_named, check_share


def git(d, *a):
    subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True)


def put(root, rel, body):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


class Site:
    """A site with an upstream and one page that already has its own card."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        remote = t / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        self.root = t / "site"
        self.root.mkdir()
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "t@t")
        git(self.root, "config", "user.name", "t")
        put(self.root, "content/share-cards.ts", 'export const shareCards = { supersuit: { image: "/og/supersuit.png" }, computer: { image: "/og/computer.png" } };\n')
        put(self.root, "app/supersuit/page.tsx", "export const metadata = pageMetadata({ image: shareCards.supersuit.image });\n")
        put(self.root, "about.html", '<meta property="og:image" content="https://x.test/og/about.png">\n')
        self.commit("base")
        git(self.root, "remote", "add", "origin", str(remote))
        git(self.root, "push", "-q", "-u", "origin", "main")

    def commit(self, msg):
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", msg)

    def check(self):
        return check_share(self.root, added="origin/main..HEAD")


class CheckShare(unittest.TestCase):
    def setUp(self):
        self.s = Site()

    def tearDown(self):
        self.s.tmp.cleanup()

    def test_a_new_page_wearing_another_pages_card_is_refused_naming_both(self):
        put(self.s.root, "app/supersuit/computer/page.tsx", "export const metadata = pageMetadata({ image: shareCards.supersuit.image });\n")
        self.s.commit("computer")
        hits, _ = self.s.check()
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["page"], "app/supersuit/computer/page.tsx")
        self.assertEqual(hits[0]["sharedWith"], "app/supersuit/page.tsx")

    def test_a_new_page_with_its_own_card_passes(self):
        put(self.s.root, "app/supersuit/computer/page.tsx", "export const metadata = pageMetadata({ image: shareCards.computer.image });\n")
        self.s.commit("computer")
        self.assertEqual(self.s.check()[0], [])

    def test_a_literal_card_path_counts_and_a_shared_one_is_refused(self):
        put(self.s.root, "app/a/page.tsx", 'export const metadata = { openGraph: { images: ["/og/a.png"] } };\n')
        self.s.commit("a")
        self.assertEqual(self.s.check()[0], [])
        git(self.s.root, "push", "-q")
        put(self.s.root, "app/b/page.tsx", 'export const metadata = { openGraph: { images: ["/og/a.png"] } };\n')
        self.s.commit("b")
        self.assertEqual([h["page"] for h in self.s.check()[0]], ["app/b/page.tsx"])

    def test_an_opengraph_image_file_beside_the_page_is_its_own_card(self):
        put(self.s.root, "app/x/page.tsx", "export default function X() { return null }\n")
        put(self.s.root, "app/x/opengraph-image.tsx", "export default function og() {}\n")
        self.s.commit("x")
        self.assertEqual(self.s.check()[0], [])

    def test_a_new_page_naming_no_card_is_refused_as_the_site_default(self):
        put(self.s.root, "app/y/page.tsx", 'export const metadata = { title: "Y" };\n')
        self.s.commit("y")
        hits, _ = self.s.check()
        self.assertEqual(hits[0]["problem"], "no-card")

    def test_plain_html_pages_are_judged_by_their_og_image(self):
        put(self.s.root, "team.html", '<meta property="og:image" content="https://x.test/og/about.png">\n')
        self.s.commit("team")
        hits, _ = self.s.check()
        self.assertEqual(hits[0]["sharedWith"], "about.html")

    def test_a_share_waiver_lets_a_deliberate_exception_through_on_the_record(self):
        put(self.s.root, "app/y/page.tsx", 'export const metadata = { title: "Y" };\n')
        git(self.s.root, "add", ".")
        git(self.s.root, "commit", "-qm", "y\n\nShare-Waiver: an internal redirect nobody shares")
        hits, waiver = self.s.check()
        self.assertEqual(hits, [])
        self.assertEqual(waiver, "an internal redirect nobody shares")

    def test_only_added_pages_are_judged_so_old_debt_never_blocks(self):
        put(self.s.root, "app/old/page.tsx", "export const metadata = pageMetadata({ image: shareCards.supersuit.image });\n")
        self.s.commit("old debt")
        git(self.s.root, "push", "-q")
        put(self.s.root, "app/old/page.tsx", 'export const metadata = pageMetadata({ image: shareCards.supersuit.image, title: "edited" });\n')
        self.s.commit("edit")
        self.assertEqual(self.s.check()[0], [])

    def test_without_a_range_every_page_is_judged(self):
        put(self.s.root, "app/old/page.tsx", "export const metadata = pageMetadata({ image: shareCards.supersuit.image });\n")
        self.s.commit("old")
        hits, _ = check_share(self.s.root)
        self.assertEqual({h["page"] for h in hits}, {"app/old/page.tsx", "app/supersuit/page.tsx"})

    def test_build_output_is_not_a_page(self):
        put(self.s.root, ".next/server/app/z/page.js", "nothing\n")
        put(self.s.root, "build/team.html", '<meta property="og:image" content="https://x.test/og/about.png">\n')
        self.s.commit("build output")
        self.assertEqual(self.s.check()[0], [])

    def test_cards_named_reads_keys_and_literal_paths(self):
        self.assertEqual(sorted(cards_named('a(shareCards.x.image) b "/og/y.jpg" c')), ["/og/y.jpg", "shareCards.x"])

    def test_the_cli_exits_1_on_a_refusal_with_json_and_0_when_clean(self):
        put(self.s.root, "app/y/page.tsx", 'export const metadata = { title: "Y" };\n')
        self.s.commit("y")
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["check-share", str(self.s.root), "--added", "origin/main..HEAD", "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["findings"][0]["page"], "app/y/page.tsx")
        git(self.s.root, "push", "-q")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["check-share", str(self.s.root), "--added", "origin/main..HEAD"]), 0)

    def test_a_range_git_refuses_exits_2_rather_than_passing(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["check-share", str(self.s.root), "--added", "nope..HEAD"]), 2)


if __name__ == "__main__":
    unittest.main()
