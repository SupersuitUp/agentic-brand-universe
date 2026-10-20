// Google Fonts availability and the stand-in rule. A brand read from a site can name a family
// that is not on Google Fonts (a licensed or self-hosted face). The board and the mark can only
// draw Google families, so such a family is replaced by the closest one by classification and
// the original is recorded, never aborting the run.
export const FALLBACKS = { serif: "Source Serif 4", sans: "Inter", mono: "IBM Plex Mono", other: "Fraunces" };

const cssUrl = (family) => "https://fonts.googleapis.com/css2?family=" + encodeURIComponent(family).replace(/%20/g, "+");

/**
 * "yes" (HTTP 200), "no" (400 or 404: Google does not know the family) or "unknown" (any other
 * status, a timeout or a network error). `fetchFn` is injectable (tests); the call gives up after 5s.
 * Unknown is never treated as "no": a transient failure must not replace someone's real font.
 */
export async function checkFont(family, { fetchFn = globalThis.fetch, timeoutMs = 5000 } = {}) {
  try {
    const r = await fetchFn(cssUrl(family), { method: "GET", signal: AbortSignal.timeout(timeoutMs) });
    if (r.status === 200) return "yes";
    if (r.status === 400 || r.status === 404) return "no";
    return "unknown";
  } catch { return "unknown"; }
}

export async function googleFontAvailable(family, opts = {}) {
  return (await checkFont(family, opts)) !== "no";
}

/** serif | sans | mono | other, from the CSS generic at the end of the stack, else from the name. */
export function classify(family, stack = "") {
  const g = String(stack).toLowerCase();
  if (/\bmonospace\b/.test(g)) return "mono";
  if (/\bsans-serif\b|\bui-sans-serif\b/.test(g)) return "sans";
  if (/\bserif\b|\bui-serif\b/.test(g)) return "serif";
  const n = String(family).toLowerCase();
  if (/mono|code|courier|consolas|typewriter/.test(n)) return "mono";
  if (/sans|grotesk|grotesque|gothic|helvetica|arial|neue|futura|gill|geometric|humanist/.test(n)) return "sans";
  if (/serif|garamond|didot|bodoni|baskerville|caslon|palatino|georgia|times|minion|roman|antiqua|slab/.test(n)) return "serif";
  return "other";
}

/** -> { family, replaced: null | { from, to, reason }, couldNotCheck?: true } */
export async function resolveFont(family, { stack = "", fetchFn } = {}) {
  const status = await checkFont(family, { fetchFn });
  if (status === "yes") return { family, replaced: null };
  if (status === "unknown") return { family, replaced: null, couldNotCheck: true };
  const to = FALLBACKS[classify(family, stack)];
  return { family: to, replaced: { from: family, to, reason: `site uses ${family}, not on Google Fonts` } };
}
