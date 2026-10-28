// SUPERCHOICES (Supersuit superproject 2026-10-28-superchoices). A works board is a multi-item review, and Gary
// ruled a review counts per decision, never per card: every work approved or re-rolled is one superchoice. The
// counter is Supersuit's (.agents/lib/supersuit-superchoices.mjs, recordReviewItem), which owns the ledger, the
// dedupe and what leaves the machine; this file only names the review and the item.
//
//   review  `abu-works:<board id>`
//   item    `<work key>@<digest of the picture judged>`, so the same tap twice is one verdict and a re-rolled
//           work's new take is a new one
//
// An older Supersuit with no counter counts nothing, and a failed count never fails the tap.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

export const takeOf = (image) => {
  try { return createHash("sha256").update(readFileSync(image)).digest("hex").slice(0, 16); } catch { return "unread"; }
};

/** Count one verdict. `counter` is the loaded supersuit-superchoices.mjs module, or null. Never throws. */
export function countVerdict(counter, { board, key, image, take = takeOf(image) } = {}) {
  try {
    if (typeof counter?.recordReviewItem !== "function") return false;
    return counter.recordReviewItem({ review: `abu-works:${board}`, item: `${key}@${take}` }).recorded === true;
  } catch { return false; }
}
