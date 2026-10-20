// A monogram mark as a standalone SVG: the letters as PATH OUTLINES (never <text>) on an accent
// tile, so the mark looks identical as a file, a favicon, an <img> and on the board. The outlines
// come from the display font (Google Fonts) via glyph-paths.py. Async because it fetches the font.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { ratio } from "./contrast.mjs";

const HELPER = join(dirname(fileURLToPath(import.meta.url)), "glyph-paths.py");
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** A font family name safe to hand to CSS and URLs: letters, digits, space, dash. */
export const safeFamily = (f) => String(f).replace(/[^\w \-]/g, "").trim();

export async function monogramSvg({ letters, treatment = "plain" }, palette, display = "Georgia") {
  const L = String(letters).slice(0, 3).toUpperCase();
  const tracking = treatment === "serif-ligature" ? -0.05 : 0;
  const r = spawnSync("python3", [HELPER, safeFamily(display), L, "--weight", "600", "--tracking", String(tracking)], { encoding: "utf8" });
  if (r.status !== 0) throw new Error("mark outlines failed: " + (r.stderr || "").trim().split("\n").pop());
  const { d } = JSON.parse(r.stdout);
  const fg = ratio(palette.ground, palette.accent) >= ratio(palette.ink, palette.accent) ? palette.ground : palette.ink;
  const rx = treatment === "enclosed" ? 50 : 14;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100" role="img" aria-label="${esc(L)}">` +
    `<rect width="100" height="100" rx="${rx}" fill="${palette.accent}"/><path d="${d}" fill="${fg}"/></svg>\n`;
}
