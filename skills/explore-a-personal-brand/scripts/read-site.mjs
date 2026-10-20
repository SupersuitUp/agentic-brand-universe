#!/usr/bin/env node
// read-site.mjs: read a live website's brand (colors, fonts, logo, icons, screenshots)
// with a throwaway headless Chrome. Usage: read-site.mjs <url> --out <dir>
// Writes <dir>/site-read.json and returns the same object. Node 22+.
import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { launch } from "./cdp.mjs";
import { validateDirection } from "./direction.mjs";

// Runs inside the page. Returns plain data.
const PAGE_SCRIPT = `(() => {
  const toHex = (c) => {
    const m = String(c).match(/rgba?\\(([^)]+)\\)/); if (!m) return null;
    const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number);
    if (p.length >= 4 && p[3] === 0) return null;
    return '#' + p.slice(0,3).map(n => Math.round(n).toString(16).padStart(2,'0')).join('');
  };
  const area = new Map();
  const vw = innerWidth;
  const els = [...document.querySelectorAll('body, body *')];
  for (const el of els) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const hex = toHex(cs.backgroundColor);
    if (hex) area.set(hex, (area.get(hex) || 0) + r.width * r.height);
  }
  const rootBg = toHex(getComputedStyle(document.documentElement).backgroundColor);
  const bodyBg = toHex(getComputedStyle(document.body).backgroundColor);
  const ground = bodyBg || rootBg || '#ffffff';
  const text = toHex(getComputedStyle(document.body).color) || '#000000';
  const accents = [];
  for (const el of document.querySelectorAll('button, .btn, [class*=button], [role=button], a')) {
    const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const bg = toHex(cs.backgroundColor);
    const isBtn = el.tagName === 'BUTTON' || /btn|button/.test(el.className) || el.getAttribute('role') === 'button';
    if (bg && bg !== ground && isBtn) accents.push({ hex: bg, from: 'button background' });
    else if (el.tagName === 'A') { const c = toHex(cs.color); if (c && c !== text && c !== ground) accents.push({ hex: c, from: 'link color' }); }
  }
  const first = (s) => String(s || '').split(',')[0].trim().replace(/^["']|["']$/g, '');
  const h = document.querySelector('h1') || document.querySelector('h2');
  const fonts = { display: first(h && getComputedStyle(h).fontFamily), body: first(getComputedStyle(document.body).fontFamily) };
  const abs = (u) => { try { return new URL(u, location.href).href; } catch { return null; } };
  const meta = (p) => { const m = document.querySelector('meta[property="'+p+'"],meta[name="'+p+'"]'); return m && m.content; };
  const link = (sel) => { const l = document.querySelector(sel); return l ? abs(l.getAttribute('href')) : null; };
  const icon = link('link[rel~="icon"]') || abs('/favicon.ico');
  const touch = link('link[rel="apple-touch-icon"]');
  const share = meta('og:image') ? abs(meta('og:image')) : null;
  // logo: an img or inline svg that says "logo", else the first img/svg in the header
  let logo = null;
  const cand = [...document.querySelectorAll('img, svg')];
  const say = (el) => ((el.getAttribute('src')||'') + ' ' + (el.getAttribute('alt')||'') + ' ' + (el.getAttribute('class')||'') + ' ' + (el.id||'') + ' ' + (el.closest('a')?.getAttribute('class')||'')).toLowerCase();
  let pick = cand.find(e => /logo/.test(say(e))) || cand.find(e => e.closest('header, nav'));
  if (pick) {
    const r = pick.getBoundingClientRect();
    if (r.width > 1 && r.height > 1) {
      logo = pick.tagName.toLowerCase() === 'svg' ? { inline: pick.outerHTML } : { url: abs(pick.getAttribute('src')) };
    }
  }
  const name = meta('og:site_name') || (document.title || '').split(/[|\\-–—:·]/)[0].trim() || (h && h.textContent.trim()) || location.hostname;
  return { name, description: meta('og:description') || meta('description') || '', ground, text,
    area: [...area].sort((a,b) => b[1]-a[1]).slice(0, 8), accents, fonts, icon, touch, share, logo };
})()`;

async function download(url, outDir, stem) {
  if (!url) return null;
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const ct = res.headers.get("content-type") || "";
    let ext = extname(new URL(url).pathname).toLowerCase();
    if (!ext) ext = ct.includes("svg") ? ".svg" : ct.includes("png") ? ".png" : ct.includes("jpeg") ? ".jpg" : ".bin";
    const file = join(outDir, stem + ext);
    writeFileSync(file, Buffer.from(await res.arrayBuffer()));
    return file;
  } catch { return null; }
}

async function shot(c, width, height, file) {
  await c.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width < 700 });
  const { data } = await c.send("Page.captureScreenshot", { format: "png" });
  writeFileSync(file, Buffer.from(data, "base64"));
  return file;
}

export async function readSite(url, { outDir } = {}) {
  outDir = resolve(outDir || ".");
  mkdirSync(outDir, { recursive: true });
  const c = await launch();
  try {
    await c.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    const loaded = c.once("Page.loadEventFired", 20000);
    await c.send("Page.navigate", { url });
    await loaded;
    await c.send("Runtime.evaluate", { expression: "document.fonts && document.fonts.ready.then(() => 1)", awaitPromise: true });
    const { result } = await c.send("Runtime.evaluate", { expression: PAGE_SCRIPT, returnByValue: true });
    const p = result.value;

    const total = p.area.reduce((s, [, a]) => s + a, 0) || 1;
    const colors = [];
    const seen = new Set();
    const add = (hex, role, area, from) => { if (hex && !seen.has(hex + role)) { seen.add(hex + role); colors.push({ hex, role, area, from }); } };
    add(p.ground, "ground", (p.area.find(([h]) => h === p.ground)?.[1] || total) / total, "body background");
    add(p.text, "text", 0, "body color");
    const acc = p.accents.find((a) => a.hex !== p.ground && a.hex !== p.text);
    if (acc) add(acc.hex, "accent", 0, acc.from);
    for (const [hex, a] of p.area) if (hex !== p.ground && hex !== p.text && hex !== acc?.hex) add(hex, "other", a / total, "background area");

    let logo = null;
    if (p.logo?.inline) { logo = join(outDir, "logo.svg"); writeFileSync(logo, p.logo.inline); }
    else if (p.logo?.url) logo = await download(p.logo.url, outDir, "logo");
    const favicon = p.icon, touchIcon = p.touch, shareImage = p.share;
    const faviconFile = await download(favicon, outDir, "favicon");

    const shots = {
      phone: await shot(c, 390, 844, join(outDir, "phone.png")),
      desktop: await shot(c, 1280, 900, join(outDir, "desktop.png")),
    };
    const out = { url, name: p.name, description: p.description, colors, fonts: p.fonts, logo, favicon, faviconFile, touchIcon, shareImage, shots };
    writeFileSync(join(outDir, "site-read.json"), JSON.stringify(out, null, 2) + "\n");
    return out;
  } finally {
    await c.close();
  }
}

const GENERIC = new Set(["serif", "sans-serif", "monospace", "system-ui", "ui-sans-serif", "ui-serif", "-apple-system", "blinkmacsystemfont", "helvetica neue", "helvetica", "arial", "georgia", "times new roman", "times", "segoe ui", "roboto"]);

/** The "site is me" case: a valid direction taken straight from a site read. */
export function toDirection(sr) {
  const role = (r) => sr.colors.find((c) => c.role === r)?.hex;
  const ground = role("ground") || "#ffffff";
  const ink = role("text") || "#111111";
  const accent = role("accent") || sr.colors.find((c) => c.role === "other")?.hex || ink;
  const font = (f, fallback) => (f && !GENERIC.has(f.toLowerCase()) ? f : fallback);
  const body = font(sr.fonts?.body, "Inter");
  const display = font(sr.fonts?.display, body);
  const letters = (sr.name || "X").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "X";
  const d = {
    name: sr.name, concept: sr.description || `The brand of ${sr.url}`,
    palette: { ground, ink, accent },
    type: { display, body },
    mark: { kind: "monogram", letters, treatment: "plain" },
    sources: [{ choice: "palette", from: "site", detail: sr.url }],
  };
  const errs = validateDirection(d);
  if (errs.length) throw new Error("toDirection produced an invalid direction: " + errs.join("; "));
  return d;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const a = process.argv.slice(2);
  const url = a.find((x) => !x.startsWith("--") && a[a.indexOf(x) - 1] !== "--out");
  const oi = a.indexOf("--out");
  if (!url || oi < 0 || !a[oi + 1]) { console.error("usage: read-site.mjs <url> --out <dir>"); process.exit(2); }
  const r = await readSite(url, { outDir: a[oi + 1] });
  console.log(JSON.stringify(r, null, 2));
}
