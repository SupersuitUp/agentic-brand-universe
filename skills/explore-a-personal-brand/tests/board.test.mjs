import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { inflateSync } from "node:zlib";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { ratio, fixContrast } from "../scripts/contrast.mjs";
import { findChrome } from "../scripts/cdp.mjs";
import { renderBoard } from "../scripts/render-board.mjs";
import { monogramSvg } from "../scripts/mark.mjs";

let HAVE = true;
try { findChrome(); } catch { HAVE = false; }
const T = (n, f, needs = true) => test(n, { skip: needs && !HAVE && "Chrome not installed" }, f);
const NET = process.env.ABU_OFFLINE ? "no network" : false;

const D = {
  name: "Sample Studio", concept: "A made-up studio for testing.",
  palette: { ground: "#101418", ink: "#e9e4da", accent: "#c8743a" },
  type: { display: "Fraunces", body: "Inter" },
  mark: { kind: "monogram", letters: "SS", treatment: "serif-ligature" }, sources: [],
};

// Minimal PNG reader: width and the first pixel (8-bit RGB/RGBA, non-interlaced).
function png(buf) {
  const w = buf.readUInt32BE(16), ct = buf[25];
  let p = 8, idat = [];
  while (p < buf.length) {
    const len = buf.readUInt32BE(p), type = buf.toString("ascii", p + 4, p + 8);
    if (type === "IDAT") idat.push(buf.subarray(p + 8, p + 8 + len));
    p += 12 + len;
  }
  const raw = inflateSync(Buffer.concat(idat));
  // first pixel has no left/up neighbour, so every filter type leaves its bytes unchanged
  const bpp = ct === 6 ? 4 : 3;
  return { width: w, height: buf.readUInt32BE(20), px: [...raw.subarray(1, 1 + bpp)] };
}

T("ratio black/white is 21", () => { assert.equal(Math.round(ratio("#000", "#fff")), 21); });

T("fixContrast lifts weak ink and notes it", () => {
  const d = structuredClone(D); d.palette.ink = "#3a3f45";
  const { direction, notes } = fixContrast(d);
  assert.ok(ratio(direction.palette.ink, d.palette.ground) >= 4.5);
  assert.equal(notes.length, 1);
  assert.match(notes[0], /ink/);
  assert.equal(D.palette.ink, "#e9e4da");
});

T("fixContrast leaves a sound palette alone", () => {
  assert.deepEqual(fixContrast(D).notes, []);
});

test("accent is lifted to 4.5:1 against ground", () => {
  const d = structuredClone(D); d.palette.accent = "#5a3a2a";
  const { direction, notes } = fixContrast(d);
  assert.ok(ratio(direction.palette.accent, d.palette.ground) >= 4.5);
  assert.ok(notes.some((n) => n.startsWith("accent")));
});

test("a lift that cannot reach its target says so", () => {
  const d = structuredClone(D); d.palette.ground = "#808080"; d.palette.ink = "#7a7a7a";
  const { direction, notes } = fixContrast(d);
  assert.ok(ratio(direction.palette.ink, "#808080") < 4.5, "white on mid grey cannot reach 4.5");
  assert.match(notes.find((n) => n.startsWith("ink")), /not reached/);
});

test("monogramSvg is outlines: paths, no <text>, the accent", { skip: NET }, async () => {
  const s = await monogramSvg(D.mark, D.palette, "Fraunces");
  assert.match(s, /^<svg[\s\S]*<\/svg>\s*$/);
  assert.ok(!s.includes("<text"));
  assert.match(s, /<path d="M[\d. ]+/);
  assert.ok(s.includes("#c8743a"));
  const py = spawnSync("python3", ["-c", "import sys,xml.dom.minidom as m;m.parseString(sys.stdin.read())"], { input: s });
  assert.equal(py.status, 0);
});

T("renderBoard writes a 2x PNG, top-left is the ground", async () => {
  const out = join(mkdtempSync(join(tmpdir(), "board-")), "b.png");
  const r = await renderBoard(D, out);
  const i = png(readFileSync(out));
  assert.equal(i.width, 780);
  assert.equal(i.height, r.cssHeight * 2);
  assert.ok(i.height > 1800 && i.height < 2600, `height ${i.height}`);
  assert.deepEqual(i.px.slice(0, 3), [0x10, 0x14, 0x18]);
  assert.equal(r.fontsFellBack, false);
});

T("the CLI persists the fixed direction and the mark", async () => {
  const dir = mkdtempSync(join(tmpdir(), "boardcli-"));
  const d = structuredClone(D); d.palette.ink = "#3a3f45";
  writeFileSync(join(dir, "dir.json"), JSON.stringify(d));
  const run = spawnSync("node", [join(import.meta.dirname, "../scripts/render-board.mjs"), join(dir, "dir.json"), "--out", join(dir, "b.png")], { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr);
  const fixed = JSON.parse(readFileSync(join(dir, "dir.fixed.json"), "utf8"));
  assert.ok(ratio(fixed.palette.ink, fixed.palette.ground) >= 4.5);
  assert.ok(fixed.contrastNotes.length >= 1);
  assert.equal(JSON.parse(readFileSync(join(dir, "dir.json"), "utf8")).palette.ink, "#3a3f45", "input untouched");
  const mark = readFileSync(join(dir, "dir.mark.svg"), "utf8");
  assert.ok(!mark.includes("<text") && mark.includes("<path"));
});
