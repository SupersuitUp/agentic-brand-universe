import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFileSync, mkdtempSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { readSite, toDirection } from "../scripts/read-site.mjs";
import { validateDirection } from "../scripts/direction.mjs";

const FIX = join(dirname(fileURLToPath(import.meta.url)), "fixtures");
const routes = {
  "/dark": ["dark-site.html", "text/html"], "/light": ["light-site.html", "text/html"],
  "/logo.svg": ["logo.svg", "image/svg+xml"], "/favicon.svg": ["favicon.svg", "image/svg+xml"],
  "/favicon.png": ["favicon.png", "image/png"], "/share.png": ["share.png", "image/png"],
  "/touch.png": ["touch.png", "image/png"],
};
let server, base;
before(async () => {
  server = createServer((req, res) => {
    const r = routes[req.url];
    if (!r) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "content-type": r[1] }); res.end(readFileSync(join(FIX, r[0])));
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => server.close());
const out = () => mkdtempSync(join(tmpdir(), "readsite-"));

test("dark site: colors, font, logo, icons, shots", async () => {
  const dir = out();
  const s = await readSite(base + "/dark", { outDir: dir });
  const by = (r) => s.colors.find((c) => c.role === r)?.hex;
  assert.equal(by("ground"), "#0b0d10");
  assert.equal(by("text"), "#e8e2d6");
  assert.equal(by("accent"), "#d9822b");
  assert.equal(s.fonts.display, "Georgia");
  assert.equal(s.name, "Night Workshop");
  assert.ok(s.logo.endsWith(".svg") && readFileSync(s.logo, "utf8").includes("<svg"));
  assert.ok(s.favicon.endsWith("/favicon.svg"));
  assert.ok(s.touchIcon.endsWith("/touch.png"));
  assert.ok(s.shareImage.endsWith("/share.png"));
  assert.ok(existsSync(s.shots.phone) && existsSync(s.shots.desktop));
  assert.ok(existsSync(join(dir, "site-read.json")));
});

test("light site: png favicon, no logo", async () => {
  const s = await readSite(base + "/light", { outDir: out() });
  assert.ok(s.favicon.endsWith(".png"));
  assert.equal(s.logo, null);
  assert.equal(s.colors.find((c) => c.role === "ground").hex, "#faf7f0");
  assert.equal(s.colors.find((c) => c.role === "accent").hex, "#1f6f8b");
  assert.equal(s.fonts.display, "Playfair Display");
});

test("toDirection gives a valid direction", async () => {
  const s = await readSite(base + "/dark", { outDir: out() });
  const d = toDirection(s);
  assert.deepEqual(validateDirection(d), []);
  assert.equal(d.palette.ground, "#0b0d10");
  assert.equal(d.mark.letters, "NW");
});

test("validateDirection names a bad hex", () => {
  const d = { name: "x", palette: { ground: "#000", ink: "#fff", accent: "orange" }, type: { display: "A", body: "B" }, mark: { kind: "monogram", letters: "X" } };
  assert.ok(validateDirection(d).some((e) => e.startsWith("palette.accent")));
});
