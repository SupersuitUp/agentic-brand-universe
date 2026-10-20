#!/usr/bin/env node
// render-board.mjs: draw a brand board PNG (390 wide, 2x) from a direction.
// Usage: render-board.mjs <direction.json> --out <png>
//
// ONE SOURCE OF TRUTH. The board draws the contrast-FIXED palette, so the CLI persists it:
// next to the input it writes <name>.fixed.json (the direction with the fixed palette and a
// `contrastNotes` array; the input is never modified) and <name>.mark.svg (the outlined mark
// drawn from that palette, unless the direction brought its own svg mark). Feed those to
// `abu seed --from <name>.fixed.json --mark <name>.mark.svg` so the canon, the live artifacts
// and the board always agree.
import { readFileSync, writeFileSync } from "node:fs";
import { resolve, dirname, basename, join } from "node:path";
import { fileURLToPath } from "node:url";
import { launch } from "./cdp.mjs";
import { ratio, fixContrast } from "./contrast.mjs";
import { monogramSvg, safeFamily } from "./mark.mjs";
import { validateDirection } from "./direction.mjs";

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const gurl = (d, b) => "https://fonts.googleapis.com/css2?family=" + encodeURIComponent(safeFamily(d)).replace(/%20/g, "+") +
  ":wght@400;600&family=" + encodeURIComponent(safeFamily(b)).replace(/%20/g, "+") + ":wght@400;500;600&display=swap";

export function boardHtml(direction, notes = [], markSvg) {
  const { palette: p, type: t } = direction;
  const sized = (px) => `<span class="m" style="width:${px}px;height:${px}px">${markSvg}</span>`;
  const r = (a, b) => ratio(a, b).toFixed(1);
  const swatch = (label, hex) => `<div class="sw"><div class="chip" style="background:${hex}"></div><b>${label}</b><code>${hex}</code></div>`;
  const dispFam = `'${safeFamily(t.display)}', Georgia, serif`, bodyFam = `'${safeFamily(t.body)}', system-ui, sans-serif`;
  return `<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="${gurl(t.display, t.body)}">
<style>
:root{--g:${p.ground};--i:${p.ink};--a:${p.accent}}
*{box-sizing:border-box} html,body{margin:0;background:var(--g);color:var(--i);width:390px}
body{font-family:${bodyFam};padding:28px 24px 36px;line-height:1.5}
h1,.disp{font-family:${dispFam};font-weight:600}
h1{font-size:34px;line-height:1.1;margin:0 0 8px}
.concept{font-family:${dispFam};font-weight:400;opacity:.8;margin:0 0 24px;font-size:15px}
.lbl{font-size:11px;letter-spacing:.12em;text-transform:uppercase;opacity:.6;margin:28px 0 10px}
.sws{display:flex;gap:10px}.sw{flex:1;font-size:12px}.chip{height:56px;border-radius:8px;border:1px solid color-mix(in srgb,var(--i) 45%,transparent);margin-bottom:6px}
.sw b{display:block;font-weight:600}.sw code{font-size:11px;opacity:.75}
.spec .d{font-family:${dispFam};font-size:32px;line-height:1.15;font-weight:600}.spec .b{font-size:16px;margin-top:6px}
.marks{display:flex;align-items:flex-end;gap:18px}.m{display:inline-block}.m svg{width:100%;height:100%;display:block}
.card{border:1px solid color-mix(in srgb,var(--i) 25%,transparent);border-radius:12px;padding:18px}
.card .k{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--a);margin-bottom:6px}
.card h2{font-family:${dispFam};font-size:22px;line-height:1.2;margin:0 0 10px}.card p{margin:0 0 10px;font-size:15px}
.card a{color:var(--a);text-decoration:underline;text-underline-offset:3px}
.c{font-size:13px;opacity:.85}.note{font-size:12px;opacity:.7;margin-top:6px}
</style></head><body>
<h1>${esc(direction.name)}</h1><p class="concept">${esc(direction.concept || "")}</p>
<div class="lbl">Palette</div>
<div class="sws">${swatch("Ground", p.ground)}${swatch("Ink", p.ink)}${swatch("Accent", p.accent)}</div>
<div class="lbl">Type</div>
<div class="spec"><div class="d">${esc(safeFamily(t.display))} ${esc(direction.name.split(" ")[0])}</div><div class="b">${esc(safeFamily(t.body))}: Small, careful work for people who notice the details.</div></div>
<div class="lbl">Mark</div>
<div class="marks">${sized(180)}${sized(32)}${sized(16)}</div>
<div class="lbl">A page</div>
<div class="card"><div class="k">A page from ${esc(direction.name)}</div><h2>How the work gets made</h2>
<p>Every piece starts as a rough sketch and gets simpler on each pass until only the useful parts remain.</p>
<p>Notes and drafts are collected in one place, <a href="#">read the latest entry</a>.</p></div>
<div class="lbl">Contrast</div>
<div class="c">text on ground ${r(p.ink, p.ground)}:1<br>accent on ground ${r(p.accent, p.ground)}:1</div>
${notes.map((n) => `<div class="note">Adjusted: ${esc(n)}</div>`).join("")}
<div id="foot" class="note"></div>
</body></html>`;
}

export async function renderBoard(direction, outPng) {
  const errs = validateDirection(direction);
  if (errs.length) throw new Error("invalid direction: " + errs.join("; "));
  const { direction: fixed, notes } = fixContrast(direction);
  const markSvg = fixed.mark.kind === "svg" ? fixed.mark.svg : await monogramSvg(fixed.mark, fixed.palette, fixed.type.display);
  const html = boardHtml(fixed, notes, markSvg);
  const c = await launch({ width: 390, height: 900 });
  try {
    await c.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 900, deviceScaleFactor: 2, mobile: false });
    const loaded = c.once("Page.loadEventFired", 30000);
    await c.send("Page.navigate", { url: "data:text/html;charset=utf-8," + encodeURIComponent(html) });
    await loaded;
    const fam = [safeFamily(fixed.type.display), safeFamily(fixed.type.body)];
    const fell = await c.send("Runtime.evaluate", {
      expression: `((d, b) => Promise.race([
        Promise.all([document.fonts.load('600 32px "' + d + '"'), document.fonts.load('16px "' + b + '"')]).then(() => document.fonts.ready).then(() => !(document.fonts.check('600 32px "' + d + '"') && document.fonts.check('16px "' + b + '"'))),
        new Promise((r) => setTimeout(() => r(true), 6000))]))(${JSON.stringify(fam[0])}, ${JSON.stringify(fam[1])})`,
      awaitPromise: true, returnByValue: true });
    if (fell.exceptionDetails) throw new Error("font check failed: " + (fell.exceptionDetails.exception?.description || fell.exceptionDetails.text));
    const fontsFellBack = fell.result.value === true;
    if (fontsFellBack) await c.send("Runtime.evaluate", { expression: `document.getElementById('foot').textContent = 'fonts fell back'` });
    const { cssContentSize } = await c.send("Page.getLayoutMetrics");
    const h = Math.ceil(cssContentSize.height);
    await c.send("Emulation.setDeviceMetricsOverride", { width: 390, height: h, deviceScaleFactor: 2, mobile: false });
    const { data } = await c.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    writeFileSync(outPng, Buffer.from(data, "base64"));
    return { out: resolve(outPng), notes, direction: fixed, markSvg, fontsFellBack, cssHeight: h };
  } finally {
    await c.close();
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const a = process.argv.slice(2);
  const oi = a.indexOf("--out");
  const file = a.find((x, i) => !x.startsWith("--") && i !== oi + 1);
  if (!file || oi < 0 || !a[oi + 1]) { console.error("usage: render-board.mjs <direction.json> --out <png>"); process.exit(2); }
  const r = await renderBoard(JSON.parse(readFileSync(file, "utf8")), a[oi + 1]);
  const base = join(dirname(resolve(file)), basename(file).replace(/\.json$/, ""));
  writeFileSync(base + ".fixed.json", JSON.stringify({ ...r.direction, contrastNotes: r.notes }, null, 2) + "\n");
  writeFileSync(base + ".mark.svg", r.markSvg);
  console.log(r.out);
  console.log("fixed direction:", base + ".fixed.json");
  console.log("mark:", base + ".mark.svg");
  for (const n of r.notes) console.log("note:", n);
  if (r.fontsFellBack) console.log("warning: fonts fell back (Google Fonts did not load)");
}
