import { test, before, after } from "node:test";
import { spawnSync } from "node:child_process";
import { findChrome } from "../scripts/cdp.mjs";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFileSync, mkdtempSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { readSite, toDirection } from "../scripts/read-site.mjs";
import { validateDirection } from "../scripts/direction.mjs";

let HAVE_CHROME = true;
try { findChrome(); } catch { HAVE_CHROME = false; }
const T = (name, fn) => test(name, { skip: !HAVE_CHROME && "Chrome not installed" }, fn);

// Independent oklch -> sRGB hex, to check Chrome's answer against the math.
function oklchHex(L, C, hDeg) {
  const h = (hDeg * Math.PI) / 180, a = C * Math.cos(h), b = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const lin = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s];
  return lin.map((v) => { v = Math.min(1, Math.max(0, v)); return Math.round(255 * (v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055)); });
}
const near = (hex, rgb, tol = 3) => [1, 3, 5].every((i, k) => Math.abs(parseInt(hex.slice(i, i + 2), 16) - rgb[k]) <= tol);

// An injectable fetch standing in for Google Fonts: 200 for the listed families, 404 otherwise.
const fakeFetch = (ok) => async (url) => {
  const fam = decodeURIComponent(new URL(url).searchParams.get("family")).replace(/\+/g, " ");
  return { status: ok.has(fam) ? 200 : 404 };
};
const SR = (fonts, stacks = {}) => ({
  url: "https://acme.test", name: "Acme Studio", description: "d",
  colors: [{ hex: "#101010", role: "ground" }, { hex: "#eeeeee", role: "text" }, { hex: "#cc5500", role: "accent" }],
  fonts, fontStacks: stacks, unresolved: {},
});

const FIX = join(dirname(fileURLToPath(import.meta.url)), "fixtures");
const routes = {
  "/dark": ["dark-site.html", "text/html"], "/light": ["light-site.html", "text/html"],
  "/logo.svg": ["logo.svg", "image/svg+xml"], "/favicon.svg": ["favicon.svg", "image/svg+xml"],
  "/favicon.png": ["favicon.png", "image/png"], "/share.png": ["share.png", "image/png"],
  "/touch.png": ["touch.png", "image/png"], "/oklch": ["oklch-site.html", "text/html"], "/inline": ["inline-logo-site.html", "text/html"],
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

T("dark site: colors, font, logo, icons, shots", async () => {
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

T("light site: png favicon, no logo", async () => {
  const s = await readSite(base + "/light", { outDir: out() });
  assert.ok(s.favicon.endsWith(".png"));
  assert.equal(s.logo, null);
  assert.equal(s.colors.find((c) => c.role === "ground").hex, "#faf7f0");
  assert.equal(s.colors.find((c) => c.role === "accent").hex, "#1f6f8b");
  assert.equal(s.fonts.display, "Playfair Display");
});

T("toDirection gives a valid direction", async () => {
  const s = await readSite(base + "/dark", { outDir: out() });
  const d = await toDirection(s, { fetchFn: fakeFetch(new Set(["Georgia", "Inter"])) });
  assert.deepEqual(validateDirection(d), []);
  assert.equal(d.palette.ground, "#0b0d10");
  assert.equal(d.mark.letters, "NW");
});

T("validateDirection names a bad hex", () => {
  const d = { name: "x", palette: { ground: "#000", ink: "#fff", accent: "orange" }, type: { display: "A", body: "B" }, mark: { kind: "monogram", letters: "X" } };
  assert.ok(validateDirection(d).some((e) => e.startsWith("palette.accent")));
});

T("oklch colors resolve to the right hex, not a default", async () => {
  const s = await readSite(base + "/oklch", { outDir: out() });
  const by = (r) => s.colors.find((c) => c.role === r)?.hex;
  assert.ok(near(by("ground"), oklchHex(0.18, 0.02, 250)), by("ground"));
  assert.ok(near(by("text"), oklchHex(0.92, 0.03, 90)), by("text"));
  assert.ok(near(by("accent"), oklchHex(0.7, 0.15, 50)), by("accent"));
  assert.deepEqual(s.unresolved, {});
});

T("inline svg logo is saved as a standalone svg", async () => {
  const s = await readSite(base + "/inline", { outDir: out() });
  const svg = readFileSync(s.logo, "utf8");
  assert.match(svg, /xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
  assert.match(svg, /viewBox="0 0 40 40"/);
  assert.ok(!svg.includes("currentColor"));
  assert.ok(svg.toLowerCase().includes("#b3261e"), "currentColor inlined as the computed color");
  const py = spawnSync("python3", ["-c", "import sys,xml.dom.minidom as m;m.parseString(sys.stdin.read())"], { input: svg });
  assert.equal(py.status, 0, py.stderr.toString());
});

T("a transparent page records why ground is unresolved instead of defaulting", async () => {
  const dir = out();
  const s = await readSite("data:text/html,<body style='color:%23123456'>x</body>", { outDir: dir });
  assert.equal(s.colors.find((c) => c.role === "ground"), undefined);
  assert.match(s.unresolved.ground, /no opaque background/);
  await assert.rejects(() => toDirection(s), /cannot make a direction/);
});

test("toDirection swaps a family not on Google Fonts for the closest one and records it", async () => {
  const f = fakeFetch(new Set(["Inter"]));
  const d = await toDirection(SR({ display: "Acme Grotesk Pro", body: "Inter" }, { display: "'Acme Grotesk Pro', sans-serif" }), { fetchFn: f });
  assert.equal(d.type.display, "Inter");
  assert.deepEqual(validateDirection(d), []);
  assert.ok(d.sources.some((x) => x.choice === "type.display" && x.detail === "site uses Acme Grotesk Pro, not on Google Fonts"));
});

test("toDirection picks the stand-in by classification", async () => {
  const f = fakeFetch(new Set());
  const pick = async (family, stack) => (await toDirection(SR({ display: family, body: family }, { display: stack, body: stack }), { fetchFn: f })).type.display;
  assert.equal(await pick("Foundry Serif", "'Foundry Serif', serif"), "Source Serif 4");
  assert.equal(await pick("Foundry Cut", "'Foundry Cut', monospace"), "IBM Plex Mono");
  assert.equal(await pick("Foundry Cut", "'Foundry Cut', cursive"), "Fraunces");
});

test("toDirection keeps an available family and records nothing", async () => {
  const d = await toDirection(SR({ display: "Fraunces", body: "Inter" }), { fetchFn: fakeFetch(new Set(["Fraunces", "Inter"])) });
  assert.equal(d.type.display, "Fraunces");
  assert.equal(d.sources.length, 1);
});
