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
import { renderBoard, boardHtml } from "../scripts/render-board.mjs";
import { monogramSvg } from "../scripts/mark.mjs";

let HAVE = true;
try { findChrome(); } catch { HAVE = false; }
const NET = process.env.ABU_OFFLINE ? "no network (ABU_OFFLINE)" : false;
const T = (n, f, o = {}) => test(n, { skip: (!HAVE && "Chrome not installed") || (o.net && NET) }, f);
const TNET = (n, f) => T(n, f, { net: true });
// Google Fonts stand-in for tests: only the listed families "exist".
const fakeFetch = (ok) => async (url) => ({ status: ok.has(decodeURIComponent(new URL(url).searchParams.get("family")).replace(/\+/g, " ")) ? 200 : 404 });

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

TNET("renderBoard writes a 2x PNG, top-left is the ground", async () => {
  const out = join(mkdtempSync(join(tmpdir(), "board-")), "b.png");
  const r = await renderBoard(D, out);
  const i = png(readFileSync(out));
  assert.equal(i.width, 780);
  assert.equal(i.height, r.cssHeight * 2);
  assert.ok(i.height > 1800 && i.height < 2600, `height ${i.height}`);
  assert.deepEqual(i.px.slice(0, 3), [0x10, 0x14, 0x18]);
  assert.equal(r.fontsFellBack, false);
});

TNET("the CLI persists the fixed direction and the mark", async () => {
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

test("monogramSvg draws in a stand-in family when the display font is not on Google Fonts", async () => {
  const asked = []; const standIns = [];
  const svg = await monogramSvg(D.mark, D.palette, "Foundry Serif", {
    fetchFn: fakeFetch(new Set(["Source Serif 4"])), stack: "'Foundry Serif', serif",
    outlines: (family) => { asked.push(family); return "M0 0L10 10Z"; }, onStandIn: (x) => standIns.push(x) });
  assert.deepEqual(asked, ["Source Serif 4"]);
  assert.equal(standIns[0].from, "Foundry Serif");
  assert.ok(svg.includes('d="M0 0L10 10Z"') && !svg.includes("<text"));
});

test("monogramSvg keeps an available family", async () => {
  const asked = [];
  await monogramSvg(D.mark, D.palette, "Fraunces", { fetchFn: fakeFetch(new Set(["Fraunces"])), outlines: (f) => { asked.push(f); return "M0 0Z"; } });
  assert.deepEqual(asked, ["Fraunces"]);
});

test("boardHtml names the font that stood in", () => {
  const html = boardHtml(D, [], "<svg/>", [{ from: "Foundry Serif", to: "Source Serif 4", reason: "site uses Foundry Serif, not on Google Fonts" }]);
  assert.match(html, /Source Serif 4 stood in for Foundry Serif/);
  assert.ok(!boardHtml(D, [], "<svg/>", []).includes("stood in"));
});

T("renderBoard never aborts for an unavailable family: it stands one in and records it", async () => {
  const d = structuredClone(D); d.type.display = "Foundry Serif";
  const out = join(mkdtempSync(join(tmpdir(), "board-")), "b.png");
  const r = await renderBoard(d, out, { fetchFn: fakeFetch(new Set(["Inter", "Source Serif 4"])), outlines: () => "M10 10L90 10L50 90Z" });
  assert.equal(r.direction.type.display, "Source Serif 4");
  assert.equal(r.standIns.length, 1);
  assert.equal(r.standIns[0].from, "Foundry Serif");
  assert.ok(r.direction.sources.some((x) => x.detail.includes("Foundry Serif")));
  assert.ok(r.markSvg.includes("M10 10L90 10L50 90Z"));
  assert.equal(png(readFileSync(out)).width, 780);
});
