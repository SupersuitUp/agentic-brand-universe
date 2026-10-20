#!/usr/bin/env node
// read-site.mjs: read a live website's brand (colors, fonts, logo, icons, screenshots)
// with a throwaway headless Chrome. Usage: read-site.mjs <url> --out <dir> [--direction <out.json>]
// --direction also writes toDirection's output (the "site is the brand" direction). Exit 1 on an
// HTTP error, a login redirect or an unreachable host (no usable read); exit 3 when the read worked
// but the site is too thin to make a direction from (site-read.json is still written).
// Writes <dir>/site-read.json and returns the same object. Node 22+.
import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { launch } from "./cdp.mjs";
import { validateDirection } from "./direction.mjs";
import { resolveFont } from "./fonts.mjs";

// Runs inside the page. Returns plain data.
const PAGE_SCRIPT = `(() => {
  // Resolve ANY CSS color (rgb, oklch, oklab, lab, lch, color(), named) to hex by letting the
  // browser paint it onto a 1x1 canvas. Returns null when transparent (alpha < 0.5) or invalid.
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  const toHex = (c) => {
    if (!c || c === 'transparent') return null;
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = 'rgba(0,0,0,0)';
    ctx.fillStyle = String(c);
    ctx.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
    if (a < 128) return null;
    return '#' + [r, g, b].map(n => n.toString(16).padStart(2, '0')).join('');
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
  const ground = bodyBg || rootBg || null;
  const text = toHex(getComputedStyle(document.body).color) || null;
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
  const stacks = { display: h ? getComputedStyle(h).fontFamily : '', body: getComputedStyle(document.body).fontFamily };
  const abs = (u) => { try { return new URL(u, location.href).href; } catch { return null; } };
  const meta = (p) => { const m = document.querySelector('meta[property="'+p+'"],meta[name="'+p+'"]'); return m && m.content; };
  const link = (sel) => { const l = document.querySelector(sel); return l ? abs(l.getAttribute('href')) : null; };
  const icon = link('link[rel~="icon"]') || abs('/favicon.ico');
  const touch = link('link[rel="apple-touch-icon"]');
  const share = meta('og:image') ? abs(meta('og:image')) : null;
  // An inline <svg> only renders inside its page. Make it standalone: xmlns, viewBox, and the
  // page's colors (currentColor and CSS-set fill/stroke) written onto the elements.
  const standaloneSvg = (svg) => {
    const clone = svg.cloneNode(true);
    const r = svg.getBoundingClientRect();
    if (!clone.getAttribute('viewBox')) clone.setAttribute('viewBox', '0 0 ' + Math.round(r.width) + ' ' + Math.round(r.height));
    if (!clone.getAttribute('width')) clone.setAttribute('width', String(Math.round(r.width)));
    if (!clone.getAttribute('height')) clone.setAttribute('height', String(Math.round(r.height)));
    const orig = [svg, ...svg.querySelectorAll('*')], copy = [clone, ...clone.querySelectorAll('*')];
    orig.forEach((o, i) => {
      const cs = getComputedStyle(o), c = copy[i];
      for (const prop of ['fill', 'stroke']) {
        const v = c.getAttribute(prop);
        if (v === 'none') continue;
        const hx = toHex(cs[prop]);
        if (hx && (v === null || v === 'currentColor')) c.setAttribute(prop, hx);
      }
      c.removeAttribute('class'); c.removeAttribute('style');
    });
    let out = new XMLSerializer().serializeToString(clone);
    const cc = toHex(getComputedStyle(svg).color) || '#000000';
    return out.replace(/currentColor/g, cc);
  };
  // logo: an img or inline svg that says "logo", else the first img/svg in the header
  let logo = null;
  const cand = [...document.querySelectorAll('img, svg')];
  const say = (el) => ((el.getAttribute('src')||'') + ' ' + (el.getAttribute('alt')||'') + ' ' + (el.getAttribute('class')||'') + ' ' + (el.id||'') + ' ' + (el.closest('a')?.getAttribute('class')||'')).toLowerCase();
  let pick = cand.find(e => /logo/.test(say(e))) || cand.find(e => e.closest('header, nav'));
  if (pick) {
    const r = pick.getBoundingClientRect();
    if (r.width > 1 && r.height > 1) {
      logo = pick.tagName.toLowerCase() === 'svg' ? { inline: standaloneSvg(pick) } : { url: abs(pick.getAttribute('src')) };
    }
  }
  const name = meta('og:site_name') || (document.title || '').split(/[|\\-–—:·]/)[0].trim() || (h && h.textContent.trim()) || location.hostname;
  return { name, description: meta('og:description') || meta('description') || '', ground, text,
    area: [...area].sort((a,b) => b[1]-a[1]).slice(0, 8), accents, fonts, stacks, icon, touch, share, logo };
})()`;

const EXT_OK = new Set([".svg", ".png", ".ico", ".jpg", ".jpeg", ".webp"]);

async function download(url, outDir, stem) {
  if (!url) return null;
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const ct = res.headers.get("content-type") || "";
    let ext = extname(new URL(url).pathname).toLowerCase();
    if (!EXT_OK.has(ext)) ext = ct.includes("svg") ? ".svg" : ct.includes("png") ? ".png" : ct.includes("jpeg") ? ".jpg" : ct.includes("webp") ? ".webp" : ct.includes("icon") ? ".ico" : ".png";
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
    await c.send("Network.enable");
    // Only the MAIN frame's document counts: a broken or login-gated iframe must not decide the read.
    const docs = new Map();
    c.on("Network.responseReceived", (e) => { if (e.type === "Document") docs.set(e.frameId, e.response); });
    const loaded = c.once("Page.loadEventFired", 20000);
    loaded.catch(() => {}); // a navigation error below throws first; do not leave this rejection unhandled
    const nav = await c.send("Page.navigate", { url });
    if (nav.errorText) throw new Error(`read-site: could not load ${url} (${nav.errorText})`);
    await loaded;
    const doc = docs.get(nav.frameId) || null;
    if (doc && doc.status >= 400) throw new Error(`read-site: ${url} answered HTTP ${doc.status}, which is an error page, not the brand`);
    if (doc && doc.url !== url && /\/(log-?in|sign-?in|sso|auth|account\/login)(\/|\?|$)/i.test(new URL(doc.url).pathname + new URL(doc.url).search)) {
      throw new Error(`read-site: ${url} redirected to ${doc.url}, which looks like a login page, not the brand`);
    }
    await c.send("Runtime.evaluate", { expression: "document.fonts && document.fonts.ready.then(() => 1)", awaitPromise: true });
    const ev = await c.send("Runtime.evaluate", { expression: PAGE_SCRIPT, returnByValue: true });
    if (ev.exceptionDetails) {
      throw new Error("reading " + url + " failed in the page: " + (ev.exceptionDetails.exception?.description || ev.exceptionDetails.text));
    }
    const p = ev.result.value;

    const total = p.area.reduce((s, [, a]) => s + a, 0) || 1;
    const colors = [];
    const seen = new Set();
    const add = (hex, role, area, from) => { if (hex && !seen.has(hex + role)) { seen.add(hex + role); colors.push({ hex, role, area, from }); } };
    const unresolved = {};
    if (p.ground) add(p.ground, "ground", (p.area.find(([h]) => h === p.ground)?.[1] || total) / total, "body background");
    else unresolved.ground = "body and html have no opaque background (the browser paints its default), so the site declares no ground";
    if (p.text) add(p.text, "text", 0, "body color");
    else unresolved.text = "body color could not be resolved to an opaque color";
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
    const out = { url, name: p.name, description: p.description, colors, fonts: p.fonts, fontStacks: p.stacks, logo, favicon, faviconFile, touchIcon, shareImage, shots, unresolved };
    writeFileSync(join(outDir, "site-read.json"), JSON.stringify(out, null, 2) + "\n");
    return out;
  } finally {
    await c.close();
  }
}

const GENERIC = new Set(["serif", "sans-serif", "monospace", "system-ui", "ui-sans-serif", "ui-serif", "-apple-system", "blinkmacsystemfont", "helvetica neue", "helvetica", "arial", "georgia", "times new roman", "times", "segoe ui", "roboto"]);

/** The read worked but the site declares too little to make a direction from (exit code 3). */
export class ThinBrandError extends Error {}

/**
 * The "site is me" case: a valid direction taken straight from a site read. A family that is not
 * on Google Fonts is replaced by the closest Google family and the original recorded in `sources`.
 * opts.fetchFn is injectable (tests).
 */
export async function toDirection(sr, opts = {}) {
  const role = (r) => sr.colors.find((c) => c.role === r)?.hex;
  const ground = role("ground"), ink = role("text");
  if (!ground || !ink) {
    throw new ThinBrandError("cannot make a direction from this site (a thin brand: the read is kept as context): " + Object.entries(sr.unresolved || {}).map(([k, v]) => `${k}: ${v}`).join("; "));
  }
  const accent = role("accent") || sr.colors.find((c) => c.role === "other")?.hex || ink;
  const sources = [{ choice: "palette", from: "site", detail: sr.url }];
  const pick = async (kind, fallback) => {
    const f = sr.fonts?.[kind];
    if (!f || GENERIC.has(f.toLowerCase())) return fallback;
    const r = await resolveFont(f, { stack: sr.fontStacks?.[kind], fetchFn: opts.fetchFn });
    if (r.replaced) sources.push({ choice: `type.${kind}`, from: "site", detail: r.replaced.reason });
    else if (r.couldNotCheck) sources.push({ choice: `type.${kind}`, from: "site", detail: `could not check whether ${f} is on Google Fonts` });
    return r.family;
  };
  const body = await pick("body", "Inter");
  const display = await pick("display", body);
  // Monogram letters are LETTERS: the first letter of each of the first two words that have one.
  // (w[0] can be punctuation or half an emoji.)
  const firstLetter = (w) => Array.from(w).find((ch) => /\p{L}/u.test(ch));
  let letters = (sr.name || "").split(/\s+/).map(firstLetter).filter(Boolean).slice(0, 2).join("").toUpperCase();
  if (!letters) { try { letters = firstLetter(new URL(sr.url).hostname.replace(/^www\./, "")) || ""; } catch {} letters = (letters || "X").toUpperCase(); }
  const d = {
    name: sr.name, concept: sr.description || `The brand of ${sr.url}`,
    palette: { ground, ink, accent },
    type: { display, body },
    mark: { kind: "monogram", letters, treatment: "plain" },
    sources,
  };
  const errs = validateDirection(d);
  if (errs.length) throw new Error("toDirection produced an invalid direction: " + errs.join("; "));
  return d;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const a = process.argv.slice(2);
  const flag = (n) => { const i = a.indexOf(n); return i < 0 ? null : a[i + 1]; };
  const valued = new Set(["--out", "--direction"].map((f) => a.indexOf(f) + 1).filter((i) => i > 0));
  const url = a.find((x, i) => !x.startsWith("--") && !valued.has(i));
  const out = flag("--out"), dirOut = flag("--direction");
  if (!url || !out) { console.error("usage: read-site.mjs <url> --out <dir> [--direction <direction.json>]"); process.exit(2); }
  let r;
  try { r = await readSite(url, { outDir: out }); }
  catch (e) { console.error(e.message); process.exit(1); }   // 1: no usable read (error page, login, unreachable)
  try {
    if (dirOut) {
      writeFileSync(dirOut, JSON.stringify(await toDirection(r), null, 2) + "\n");
      console.error("direction written to " + dirOut);
    }
  } catch (e) {
    console.log(JSON.stringify(r, null, 2));
    console.error(e.message);
    process.exit(e instanceof ThinBrandError ? 3 : 1);        // 3: read ok, thin brand
  }
  console.log(JSON.stringify(r, null, 2));
}
