// The whole seam, once: render-board's CLI output goes through `node bin/abu.mjs seed`, the way the
// skill does it. Needs Chrome, uv and network (Google Fonts); skips honestly without them.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFile, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { findChrome } from "../scripts/cdp.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ABU = join(HERE, "../../../bin/abu.mjs");
const BOARD = join(HERE, "../scripts/render-board.mjs");
const run = (args) => new Promise((res) => execFile("node", args, { encoding: "utf8" }, (e, stdout, stderr) => res({ status: e ? (e.code ?? 1) : 0, stdout, stderr })));
let why = false;
try { findChrome(); } catch { why = "Chrome not installed"; }
if (!why && spawnSync("uv", ["--version"]).error) why = "uv not installed";
if (!why && process.env.ABU_OFFLINE) why = "no network (ABU_OFFLINE)";

test("render-board CLI output seeds a universe through bin/abu.mjs", { skip: why }, async () => {
  const dir = mkdtempSync(join(tmpdir(), "pipeline-"));
  const d = { name: "Sample Studio", concept: "A made-up studio.",
    palette: { ground: "#101418", ink: "#e9e4da", accent: "#e2703a", lightGround: "#f7f3ea", lightInk: "#1a1a1a" },
    type: { display: "Fraunces", body: "Inter" }, mark: { kind: "monogram", letters: "SS" } };
  writeFileSync(join(dir, "d.json"), JSON.stringify(d));
  let r = await run([BOARD, join(dir, "d.json"), "--out", join(dir, "d.png")]);
  assert.equal(r.status, 0, r.stderr);
  const fixed = JSON.parse(readFileSync(join(dir, "d.fixed.json"), "utf8"));
  assert.ok(fixed.palette.lightAccent, "the board derived a light accent");

  const U = join(dir, "u");
  r = await run([ABU, "init", U, "--name", "sample-brand"]);
  assert.equal(r.status, 0, r.stdout + r.stderr);
  writeFileSync(join(dir, "brief.md"), "# Brief\n");
  r = await run([ABU, "seed", U, "--from", join(dir, "d.fixed.json"), "--brief", join(dir, "brief.md"),
    "--mark", join(dir, "d.mark.svg"), "--board", join(dir, "d.png")]);
  assert.equal(r.status, 0, r.stdout + r.stderr);

  const tokens = JSON.parse(readFileSync(join(U, "canon/craft/palette.json"), "utf8")).tokens;
  assert.equal(tokens.accent, fixed.palette.accent);
  assert.equal(tokens.lightAccent, fixed.palette.lightAccent);
  const u = JSON.parse(readFileSync(join(U, "universe.json"), "utf8"));
  assert.equal(u.identity.surfaces["artifact-light"].roles.accent, "lightAccent");
  assert.equal(u.identity.register.anchor, "reference/register/board.png");
  const mark = readFileSync(join(U, "marks/mark.svg"), "utf8"), fav = readFileSync(join(U, "marks/favicon.svg"), "utf8");
  assert.ok(!mark.includes("<text") && mark.includes("<path"));
  assert.ok(existsSync(join(U, "marks/favicon.svg.recipe.json")) && fav.includes('viewBox="0 0 100 100"'));
  r = await run([ABU, "validate", U]);
  assert.equal(r.status, 0, r.stdout + r.stderr);
});

test("seed with a missing mark file fails cleanly, writing nothing", { skip: why }, async () => {
  const dir = mkdtempSync(join(tmpdir(), "pipeline-"));
  writeFileSync(join(dir, "d.json"), JSON.stringify({ name: "N", palette: { ground: "#000", ink: "#fff", accent: "#f80" }, type: { display: "A", body: "B" }, mark: { kind: "monogram", letters: "N" } }));
  writeFileSync(join(dir, "b.md"), "# b");
  const U = join(dir, "u");
  await run([ABU, "init", U, "--name", "t"]);
  const r = await run([ABU, "seed", U, "--from", join(dir, "d.json"), "--brief", join(dir, "b.md"), "--mark", join(dir, "nope.svg")]);
  assert.equal(r.status, 1);
  assert.ok(!existsSync(join(U, "canon/craft/palette.json")));
});
