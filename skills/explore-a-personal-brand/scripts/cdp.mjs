// Minimal Chrome DevTools Protocol client: launch a throwaway headless Chrome, talk to one
// page over the global WebSocket (Node 22+). No puppeteer, no playwright.
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, existsSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME_CANDIDATES = [
  process.env.CHROME_BIN,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].filter(Boolean);

export function findChrome() {
  const c = CHROME_CANDIDATES.find((p) => existsSync(p));
  if (!c) throw new Error("Chrome not found; set CHROME_BIN");
  return c;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Launch with up to 3 attempts: a headless Chrome occasionally dies at startup under load.
 * A missing binary is not retried. Every failed attempt kills its Chrome and removes its profile.
 */
export async function launch(opts = {}) {
  const bin = findChrome();
  let err;
  for (let i = 0; i < 3; i++) {
    try { return await launchOnce(bin, opts); } catch (e) { err = e; await sleep(300); }
  }
  throw err;
}

async function launchOnce(bin, { width = 1280, height = 900 } = {}) {
  const dir = mkdtempSync(join(tmpdir(), "abu-cdp-"));
  const proc = spawn(bin, [
    "--headless=new", "--remote-debugging-port=0", `--user-data-dir=${dir}`,
    "--no-first-run", "--no-default-browser-check", "--disable-gpu",
    "--hide-scrollbars", `--window-size=${width},${height}`, "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });
  const cleanup = () => { try { proc.kill(); } catch {} try { rmSync(dir, { recursive: true, force: true }); } catch {} };
  try {
  let stderr = "";
  proc.stderr.on("data", (b) => { stderr += b; });

  let port = null;
  for (let i = 0; i < 100 && !port; i++) {
    const f = join(dir, "DevToolsActivePort");
    if (existsSync(f)) { const l = readFileSync(f, "utf8").split("\n"); if (l.length >= 2 && l[1]) port = Number(l[0]); }
    if (!port && proc.exitCode !== null) throw new Error("Chrome exited early: " + stderr.slice(-300));
    if (!port) await sleep(100);
  }
  if (!port) throw new Error("Chrome gave no DevTools port: " + stderr.slice(-300));

  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = targets.find((t) => t.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error("websocket failed")); });

  let id = 0;
  const pending = new Map();
  const listeners = new Map();
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { res, rej } = pending.get(m.id); pending.delete(m.id);
      m.error ? rej(new Error(`${m.error.message}`)) : res(m.result);
    } else if (m.method && listeners.has(m.method)) {
      for (const fn of [...listeners.get(m.method)]) fn(m.params);
    }
  };

  const send = (method, params = {}) => new Promise((res, rej) => {
    const n = ++id; pending.set(n, { res, rej });
    ws.send(JSON.stringify({ id: n, method, params }));
  });
  const once = (method, timeout = 15000) => new Promise((res, rej) => {
    const t = setTimeout(() => rej(new Error(`timeout waiting for ${method}`)), timeout);
    const fn = (p) => { clearTimeout(t); listeners.get(method).delete(fn); res(p); };
    if (!listeners.has(method)) listeners.set(method, new Set());
    listeners.get(method).add(fn);
  });
  const on = (method, fn) => { if (!listeners.has(method)) listeners.set(method, new Set()); listeners.get(method).add(fn); };
  const close = async () => {
    try { ws.close(); } catch {}
    proc.kill();
    await sleep(100);
    try { rmSync(dir, { recursive: true, force: true }); } catch {}
  };
  await send("Page.enable");
  await send("Runtime.enable");
  return { send, once, on, close, port };
  } catch (e) { cleanup(); throw e; }
}
