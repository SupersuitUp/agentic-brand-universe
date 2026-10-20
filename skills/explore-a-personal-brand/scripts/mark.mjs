// A monogram mark as a standalone SVG: the letters as PATH OUTLINES (never <text>) on an accent
// tile, so the mark looks identical as a file, a favicon, an <img> and on the board. The outlines
// come from the display font (Google Fonts) via glyph-paths.py. Async because it fetches the font.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { ratio } from "./contrast.mjs";
import { resolveFont } from "./fonts.mjs";

const HELPER = join(dirname(fileURLToPath(import.meta.url)), "glyph-paths.py");
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** A font family name safe to hand to CSS and URLs: letters, digits, space, dash. */
export const safeFamily = (f) => String(f).replace(/[^\w \-]/g, "").trim();

// The helper needs fontTools and brotli. It runs under uv with pinned versions, so nothing is
// ever installed into a system Python (PEP 668 refuses that on Homebrew) and nothing floats.
export const PINS = { fonttools: "4.61.1", brotli: "1.2.0" };
const defaultRun = (cmd, args) => spawnSync(cmd, args, { encoding: "utf8" });

/** Outlines via the python helper. Injectable (tests) as opts.outlines(family, letters, tracking) -> path data. */
function pythonOutlines(family, letters, tracking, run = defaultRun) {
  const r = run("uv", ["run", "--quiet", "--with", `fonttools==${PINS.fonttools}`, "--with", `brotli==${PINS.brotli}`,
    HELPER, safeFamily(family), letters, "--weight", "600", "--tracking", String(tracking)]);
  if (r.error?.code === "ENOENT") throw new Error("mark outlines need uv, which is not installed: install uv: brew install uv");
  if (r.status !== 0) throw new Error("mark outlines failed: " + (r.stderr || "").trim().split("\n").pop());
  return JSON.parse(r.stdout).d;
}

/**
 * opts.fetchFn and opts.outlines are injectable. If `display` is not on Google Fonts the mark is
 * drawn in the closest Google family instead, and opts.onStandIn({from,to,reason}) is told.
 */
export async function monogramSvg({ letters, treatment = "plain" }, palette, display = "Georgia", opts = {}) {
  const L = String(letters).slice(0, 3).toUpperCase();
  const tracking = treatment === "serif-ligature" ? -0.05 : 0;
  const font = await resolveFont(safeFamily(display), { fetchFn: opts.fetchFn, stack: opts.stack });
  if (font.replaced && opts.onStandIn) opts.onStandIn(font.replaced);
  const d = opts.outlines ? opts.outlines(font.family, L, tracking) : pythonOutlines(font.family, L, tracking, opts.run);
  const fg = ratio(palette.ground, palette.accent) >= ratio(palette.ink, palette.accent) ? palette.ground : palette.ink;
  const rx = treatment === "enclosed" ? 50 : 14;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100" role="img" aria-label="${esc(L)}">` +
    `<rect width="100" height="100" rx="${rx}" fill="${palette.accent}"/><path d="${d}" fill="${fg}"/></svg>\n`;
}
