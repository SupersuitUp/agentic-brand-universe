// Google Fonts availability and the stand-in rule. A brand read from a site can name a family
// that is not on Google Fonts (a licensed or self-hosted face). The board and the mark can only
// draw Google families, so such a family is replaced by the closest one by classification and
// the original is recorded, never aborting the run.
export const FALLBACKS = { serif: "Source Serif 4", sans: "Inter", mono: "IBM Plex Mono", other: "Fraunces" };

const cssUrl = (family) => "https://fonts.googleapis.com/css2?family=" + encodeURIComponent(family).replace(/%20/g, "+");

/**
 * Is `family` on Google Fonts? `fetchFn` is injectable (tests). A network failure answers
 * true: not knowing is no reason to change someone's brand.
 */
export async function googleFontAvailable(family, { fetchFn = globalThis.fetch } = {}) {
  try {
    const r = await fetchFn(cssUrl(family), { method: "GET" });
    return r.status === 200;
  } catch { return true; }
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

/** -> { family, replaced: null | { from, to, reason } } */
export async function resolveFont(family, { stack = "", fetchFn } = {}) {
  if (await googleFontAvailable(family, { fetchFn })) return { family, replaced: null };
  const to = FALLBACKS[classify(family, stack)];
  return { family: to, replaced: { from: family, to, reason: `site uses ${family}, not on Google Fonts` } };
}
