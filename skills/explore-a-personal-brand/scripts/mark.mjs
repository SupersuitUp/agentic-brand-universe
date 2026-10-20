// A monogram mark as SVG: the letters on an accent tile, in the display font. The tile makes
// it read at 16px; the letter color is whichever of ground/ink contrasts better with the accent.
import { ratio } from "./contrast.mjs";

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export function monogramSvg({ letters, treatment = "plain" }, palette, display = "Georgia") {
  const L = esc(String(letters).slice(0, 3).toUpperCase());
  const fg = ratio(palette.ground, palette.accent) >= ratio(palette.ink, palette.accent) ? palette.ground : palette.ink;
  const n = L.length;
  const size = n === 1 ? 64 : n === 2 ? 48 : 36;
  const family = `'${esc(display)}', Georgia, 'Times New Roman', serif`;
  let tile, spacing = 0, weight = 600, style = "normal";
  switch (treatment) {
    case "serif-ligature": spacing = -4; tile = `<rect width="100" height="100" rx="14" fill="${palette.accent}"/>`; style = "italic"; break;
    case "enclosed": tile = `<rect width="100" height="100" rx="50" fill="${palette.accent}"/>`; break;
    default: tile = `<rect width="100" height="100" rx="14" fill="${palette.accent}"/>`;
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100" role="img" aria-label="${L}">` +
    tile +
    `<text x="50" y="50" text-anchor="middle" dominant-baseline="central" font-family="${family}" font-size="${size}" font-weight="${weight}" font-style="${style}" letter-spacing="${spacing}" fill="${fg}">${L}</text></svg>\n`;
}
