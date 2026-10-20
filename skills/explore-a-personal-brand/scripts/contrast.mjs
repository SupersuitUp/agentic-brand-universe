// WCAG contrast helpers and the repair a brand board applies before showing a palette.
const expand = (h) => (h.length === 4 ? "#" + [...h.slice(1)].map((c) => c + c).join("") : h).toLowerCase();
const rgb = (h) => { h = expand(h); return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)); };
const hex = (v) => "#" + v.map((n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, "0")).join("");
const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
export const luminance = (h) => { const [r, g, b] = rgb(h); return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b); };

/** WCAG contrast ratio of two hex colors, 1 to 21. */
export function ratio(a, b) {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

/** Move `fg` toward white or black (whichever helps against `bg`) until it reaches `min`. */
export function lift(fg, bg, min) {
  if (ratio(fg, bg) >= min) return fg;
  const target = luminance(bg) < 0.4 ? [255, 255, 255] : [0, 0, 0];
  const base = rgb(fg);
  for (let t = 0.02; t <= 1.0001; t += 0.02) {
    const c = hex(base.map((v, i) => v + (target[i] - v) * t));
    if (ratio(c, bg) >= min) return c;
  }
  return hex(target);
}

/** Lift ink to 4.5:1 and accent to 3:1 against ground (and the light pair likewise). Pure. */
export function fixContrast(direction) {
  const d = JSON.parse(JSON.stringify(direction));
  const notes = [];
  const p = d.palette;
  const fix = (key, bgKey, min, label) => {
    if (!p[key] || !p[bgKey]) return;
    const before = ratio(p[key], p[bgKey]);
    if (before >= min) return;
    const next = lift(p[key], p[bgKey], min);
    notes.push(`${label} ${p[key]} on ${p[bgKey]} was ${before.toFixed(1)}:1, lifted to ${next} (${ratio(next, p[bgKey]).toFixed(1)}:1)`);
    p[key] = next;
  };
  fix("ink", "ground", 4.5, "ink");
  fix("accent", "ground", 3, "accent");
  fix("lightInk", "lightGround", 4.5, "light ink");
  return { direction: d, notes };
}
