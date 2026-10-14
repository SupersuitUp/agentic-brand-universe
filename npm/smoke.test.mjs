// The npm package's contract: the PACKED tarball, installed into a fresh directory outside this
// repo, gives a working `abu` that runs the bundled engine, with no path back into the source tree
// or a Claude plugin cache. And its version is the plugin's, because the npm version IS the engine
// version a surface pins.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));

test("the npm version is the plugin version", () => {
  const plugin = JSON.parse(readFileSync(join(ROOT, ".claude-plugin", "plugin.json"), "utf8"));
  assert.equal(pkg.version, plugin.version);
});

test("the packed tarball installs and its abu runs the gate, from outside the repo", () => {
  const t = mkdtempSync(join(tmpdir(), "abu-npm-"));
  const packed = JSON.parse(execFileSync("npm", ["pack", "--json", "--pack-destination", t], { cwd: ROOT, encoding: "utf8" }))[0];
  const names = packed.files.map((f) => f.path);
  assert.ok(names.includes("bin/abu.mjs") && names.includes("engine/agenticstory/cli.py") && names.includes("engine/agenticstory/kit.py"));
  assert.ok(!names.some((n) => n.startsWith("engine/tests/") || n.startsWith("skills/") || n.startsWith("site/")), "only the engine and what it reads ship");
  const app = join(t, "app");
  mkdirSync(app);
  writeFileSync(join(app, "package.json"), "{}");
  execFileSync("npm", ["i", "--silent", "--no-audit", "--no-fund", join(t, packed.filename)], { cwd: app });
  const abu = join(app, "node_modules", ".bin", "abu");
  const env = { ...process.env, PYTHONPATH: "" };

  // A universe whose palette is one teal, and a surface that adds a green.
  const u = join(t, "u");
  mkdirSync(join(u, "canon", "craft"), { recursive: true });
  mkdirSync(join(u, "canon", "entities"), { recursive: true });
  writeFileSync(join(u, "universe.json"), JSON.stringify({ id: "t", name: "T", assetRoot: ".", identity: {} }));
  writeFileSync(join(u, "canon", "craft", "the-ascent.json"), JSON.stringify({ id: "the-ascent", kind: "register-rule", name: "A", summary: "s", tokens: { teal: { hex: "#105971" } } }));
  writeFileSync(join(u, "canon", "craft", "brand-kit.json"), JSON.stringify({ id: "brand-kit", kind: "kit", name: "K", summary: "s", tokensFrom: "canon/craft/the-ascent.json#tokens", pieces: [], noGos: [] }));
  writeFileSync(join(app, "ok.css"), ".a{color:#105971}\n");
  writeFileSync(join(app, "bad.css"), ".a{color:#00ff00}\n");

  const ok = spawnSync(abu, ["check-kit", u, join(app, "ok.css")], { encoding: "utf8", env });
  assert.equal(ok.status, 0, ok.stdout + ok.stderr);
  const bad = spawnSync(abu, ["check-kit", u, join(app, "bad.css")], { encoding: "utf8", env });
  assert.equal(bad.status, 1);
  assert.match(bad.stdout, /OFF-PALETTE #00FF00/);
  assert.doesNotMatch(bad.stdout + bad.stderr, new RegExp(ROOT.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), "nothing reaches back into the source repo");

  const nopy = spawnSync(abu, ["--help"], { encoding: "utf8", env: { ...env, ABU_PYTHON: "/nonexistent/python3" } });
  assert.equal(nopy.status, 127);
  assert.match(nopy.stderr, /install python3/);
  rmSync(t, { recursive: true, force: true });
});
