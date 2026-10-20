import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { inflateSync } from "node:zlib";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ratio, fixContrast } from "../scripts/contrast.mjs";
import { monogramSvg } from "../scripts/mark.mjs";
import { renderBoard } from "../scripts/render-board.mjs";

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

test("ratio black/white is 21", () => { assert.equal(Math.round(ratio("#000", "#fff")), 21); });

test("fixContrast lifts weak ink and notes it", () => {
  const d = structuredClone(D); d.palette.ink = "#3a3f45";
  const { direction, notes } = fixContrast(d);
  assert.ok(ratio(direction.palette.ink, d.palette.ground) >= 4.5);
  assert.equal(notes.length, 1);
  assert.match(notes[0], /ink/);
  assert.equal(D.palette.ink, "#e9e4da");
});

test("fixContrast leaves a sound palette alone", () => {
  assert.deepEqual(fixContrast(D).notes, []);
});

test("monogramSvg is svg with letters and accent", () => {
  const s = monogramSvg(D.mark, D.palette, "Fraunces");
  assert.match(s, /^<svg[\s\S]*<\/svg>\s*$/);
  assert.ok(s.includes("SS") && s.includes("#c8743a"));
});

test("renderBoard writes a 2x PNG whose top-left pixel is the ground", async () => {
  const out = join(mkdtempSync(join(tmpdir(), "board-")), "b.png");
  await renderBoard(D, out);
  const i = png(readFileSync(out));
  assert.equal(i.width, 780);
  assert.ok(i.height > 900);
  assert.deepEqual(i.px.slice(0, 3), [0x10, 0x14, 0x18]);
});
