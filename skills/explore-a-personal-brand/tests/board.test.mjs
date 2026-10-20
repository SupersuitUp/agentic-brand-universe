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
import { validateDirection } from "../scripts/direction.mjs";

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

T("a stand-in on an interview direction is attributed to the interview, not a site", async () => {
  const d = structuredClone(D); d.type.display = "Foundry Serif";
  d.sources = [{ choice: "type", from: "interview", detail: "q3: likes old books" }];
  const r = await renderBoard(d, join(mkdtempSync(join(tmpdir(), "board-")), "b.png"), { fetchFn: fakeFetch(new Set(["Inter"])), outlines: () => "M0 0Z" });
  const s = r.direction.sources.find((x) => x.detail.includes("not on Google Fonts"));
  assert.equal(s.from, "interview");
});

T("a font that could not be checked is kept and named on the board", async () => {
  const r = await renderBoard(D, join(mkdtempSync(join(tmpdir(), "board-")), "b.png"), { fetchFn: async () => ({ status: 500 }), outlines: () => "M0 0Z" });
  assert.equal(r.direction.type.display, "Fraunces");
  assert.equal(r.standIns.length, 0);
  assert.ok(r.direction.sources.some((x) => x.detail.startsWith("could not check")));
  assert.match(boardHtml(D, [], "<svg/>", [], ["Fraunces"]), /could not check whether Fraunces is on Google Fonts/);
});

const LIGHT = () => { const d = structuredClone(D); d.palette.accent = "#e2703a"; d.palette.lightGround = "#f7f3ea"; d.palette.lightInk = "#1a1a1a"; return d; };

test("fixContrast derives a light accent that reaches 4.5:1 on the light ground", () => {
  const d = LIGHT();
  assert.ok(ratio("#e2703a", "#f7f3ea") < 3, "the e2e case: the dark accent is weak on light");
  const { direction, notes } = fixContrast(d);
  assert.ok(ratio(direction.palette.lightAccent, "#f7f3ea") >= 4.5);
  assert.equal(direction.palette.accent, "#e2703a", "the dark-mode accent is untouched");
  assert.ok(notes.some((n) => n.startsWith("light accent")));
  assert.equal(d.palette.lightAccent, undefined, "input untouched");
});

test("fixContrast keeps a passing lightAccent, lifts a failing one, and adds none without a light ground", () => {
  const ok = LIGHT(); ok.palette.lightAccent = "#8a3a10";
  assert.equal(fixContrast(ok).direction.palette.lightAccent, "#8a3a10");
  const weak = LIGHT(); weak.palette.lightAccent = "#e2703a";
  assert.ok(ratio(fixContrast(weak).direction.palette.lightAccent, "#f7f3ea") >= 4.5);
  assert.equal(fixContrast(D).direction.palette.lightAccent, undefined);
});

test("the derived light accent is a darkening of the accent (same hue family)", () => {
  const la = fixContrast(LIGHT()).direction.palette.lightAccent;
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(la.slice(i, i + 2), 16));
  assert.ok(r >= g && g >= b, la);
});

test("the JS validator knows lightAccent", () => {
  const d = LIGHT(); d.palette.lightAccent = "nope";
  assert.ok(validateDirection(d).some((e) => e.startsWith("palette.lightAccent")));
  d.palette.lightAccent = "#8a3a10";
  assert.deepEqual(validateDirection(d), []);
});

test("the board shows the light accent", () => {
  const { direction } = fixContrast(LIGHT());
  const html = boardHtml(direction, [], "<svg/>");
  assert.match(html, /Light accent/);
  assert.ok(html.includes(direction.palette.lightAccent));
});

test("the mark runs its helper under uv with pinned packages, never pip", async () => {
  let seen;
  const run = (cmd, args) => { seen = { cmd, args }; return { status: 0, stdout: JSON.stringify({ d: "M0 0Z" }), stderr: "" }; };
  await monogramSvg(D.mark, D.palette, "Fraunces", { fetchFn: fakeFetch(new Set(["Fraunces"])), run });
  assert.equal(seen.cmd, "uv");
  assert.deepEqual(seen.args.slice(0, 5), ["run", "--quiet", "--with", "fonttools==4.61.1", "--with"]);
  assert.ok(seen.args.includes("brotli==1.2.0"));
  assert.ok(seen.args.some((a) => a.endsWith("glyph-paths.py")));
});

test("a missing uv fails clearly", async () => {
  const run = () => ({ error: Object.assign(new Error("spawn uv ENOENT"), { code: "ENOENT" }), status: null, stdout: "", stderr: "" });
  await assert.rejects(() => monogramSvg(D.mark, D.palette, "Fraunces", { fetchFn: fakeFetch(new Set(["Fraunces"])), run }), /install uv: brew install uv/);
});

test("a single-weight Google family (Bebas Neue) outlines for real", { skip: NET || (spawnSync("uv", ["--version"]).error ? "uv not installed" : false) }, async () => {
  const svg = await monogramSvg({ letters: "BN", treatment: "plain" }, D.palette, "Bebas Neue");
  assert.match(svg, /<path d="M/);
});

test("the JS validator agrees with the shared fixtures (the Python one runs the same file)", () => {
  const fx = JSON.parse(readFileSync(join(import.meta.dirname, "fixtures/directions.json"), "utf8"));
  for (const v of fx.valid) assert.deepEqual(validateDirection(v.direction), [], v.name);
  for (const bad of fx.invalid) {
    const errs = validateDirection(bad.direction);
    assert.ok(errs.some((e) => e.startsWith(bad.expect)), `${bad.name}: ${JSON.stringify(errs)}`);
  }
});
