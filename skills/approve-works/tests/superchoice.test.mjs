// A works board counts one superchoice per work's verdict (Gary, 2026-10-28: per decision, never per card),
// through Supersuit's counter, keyed so a resent tap is one verdict and a re-rolled work's new take is another.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { countVerdict } from "../frapps/superchoice.mjs";

function fakeCounter() {
  const seen = new Set();
  const calls = [];
  return { calls, recordReviewItem: (a) => { calls.push(a); const k = `${a.review}|${a.item}`; const fresh = !seen.has(k); seen.add(k); return { recorded: fresh }; } };
}

test("each work's verdict is one superchoice; the same tap twice is one; a new take is another", () => {
  const dir = mkdtempSync(join(tmpdir(), "works-sc-"));
  const img = (n, bytes) => { const p = join(dir, `${n}.png`); writeFileSync(p, bytes); return p; };
  const c = fakeCounter();
  const a = img("a", "A1"), b = img("b", "B1");
  assert.equal(countVerdict(c, { board: "heroes", key: "a", image: a }), true);
  assert.equal(countVerdict(c, { board: "heroes", key: "b", image: b }), true);
  assert.equal(countVerdict(c, { board: "heroes", key: "b", image: b }), false, "a resent tap");
  writeFileSync(b, "B2");
  assert.equal(countVerdict(c, { board: "heroes", key: "b", image: b }), true, "the re-rolled take");
  assert.ok(c.calls.every((x) => x.review === "abu-works:heroes" && /^[ab]@[0-9a-f]{16}$/.test(x.item)));
});

test("an older Supersuit with no counter, or a counter that throws, never fails the tap", () => {
  assert.equal(countVerdict(null, { board: "x", key: "a", image: "/nope.png" }), false);
  assert.equal(countVerdict({ recordReviewItem: () => { throw new Error("boom"); } }, { board: "x", key: "a", image: "/nope.png" }), false);
});
