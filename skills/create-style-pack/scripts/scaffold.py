#!/usr/bin/env python3
"""
scaffold.py — scaffold a Style Pack (SPEC §4.7): a portable <pack>/pack.json + refs/.

Copies the blessed reference images INTO the pack (self-contained, §3a), writes the
manifest, and validates that every ref resolves and the anchor is one of the refs.
A pack without a `gate` is rejected: a gateless pack is a mood board, not a Style Pack.

Usage:
  python3 scaffold.py --dir <pack-dir> --id <id> --name "<name>" \\
    --anchor <path-to-anchor.png> \\
    --ref <path.png> [--ref ...]            (3-8 total, anchor auto-included) \\
    --style-line "<one-line look>" \\
    --palette-ground '#0a1030,#141c46' [--palette-fill ... --palette-line ...] \\
    --reject <pole> [--reject ...] \\
    --gate "<assertion>" [--gate ...]       (>=1 required) \\
    --text-policy none|diegetic|furniture    (required, SPEC 4.7) \\
    --max-elements 5 \\
    [--require-entity <canon-entity-id> ...] (SPEC 4.7 requiredEntities: a render in this
                                              pack must bind each via --entity or it refuses)

FROM AN EXPLORE PICK (SPEC v0.62, issue #60): instead of --anchor/--ref, name the explore
output and the direction the operator picked. Every subject's picked roll becomes a ref
(byte-identical, its recipe beside it, named for the subject), each is blessed by whoever
picked, and pack.json records the pick, the directions considered and the decision:

  python3 scaffold.py --dir <pack> --id <id> --name "<name>" --style-line ... --gate ... \\
    --text-policy none --from-explore <explore-out-dir> --pick A-ascent-poster \\
    --decided-by "<who>" [--decided-on YYYY-MM-DD] --verbatim "<their words>" \\
    [--scope-use <book>:<role> ...] [--scope-subjects "..."] [--scope-never "..."]

<explore-out-dir> is one explore run (`<id>.png` files) or a folder of runs, one per subject
(`<subject>/<id>.png`). --scope-use writes the pack's TYPED scope, which generate.py enforces.
"""
import argparse, datetime, hashlib, json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bless_ref  # noqa: E402  (one writer of a blessing marker)

# Files an explore run writes that are not directions: the sheets.
_SHEETS = ("contact-sheet", "contact_sheet", "at-size-sheet", "sheet", "montage")


def _variants(d):
    """The direction ids in one explore run: its pngs, minus the sheets."""
    return sorted(os.path.splitext(n)[0] for n in os.listdir(d)
                  if n.lower().endswith(".png") and not any(t in n.lower() for t in _SHEETS))


def explore_picks(dirs, pick):
    """`([(src, dest-name)], considered)` for `pick` across explore runs, or exits naming why.

    A run is a dir holding `<id>.png`; a dir holding none but containing runs is a folder of
    runs, one per subject, and each subject's pick is named for the subject. A subject missing
    the pick is REFUSED by name: a pack built from two of three picks reads as all three.
    """
    runs = []
    for d in dirs:
        d = os.path.abspath(os.path.expanduser(d))
        if not os.path.isdir(d):
            sys.exit(f"scaffold: --from-explore {d} is not a directory")
        if _variants(d):
            runs.append((d, None))
            continue
        subs = [os.path.join(d, n) for n in sorted(os.listdir(d))
                if os.path.isdir(os.path.join(d, n)) and _variants(os.path.join(d, n))]
        if not subs:
            sys.exit(f"scaffold: --from-explore {d} holds no explore roll (<id>.png) and no "
                     f"folder of runs")
        runs += [(s, os.path.basename(s)) for s in subs]
    considered, out, absent = [], [], []
    for d, subject in runs:
        have = _variants(d)
        considered += [v for v in have if v not in considered]
        src = os.path.join(d, pick + ".png")
        if os.path.exists(src):
            out.append((src, subject))
        else:
            absent.append(f"{subject or d}: has {', '.join(have)}")
    if absent:
        sys.exit(f"scaffold: --pick {pick!r} is missing from " + str(len(absent))
                 + " run(s), refusing a partial promotion:\n  " + "\n  ".join(absent))
    one = len(out) == 1
    return [(src, (pick if one or not subj else subj) + ".png") for src, subj in out], considered

def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def _same_bytes(a, b):
    """Identical content must REUSE the name, never fork to `<stem>-1`.

    The rename loop keeps two DIFFERENT sources sharing a basename from clobbering
    each other. On a re-run, though, the file already in refs/ is a byte-identical
    copy of the same source, and renaming it points the manifest at a copy whose
    `.recipe.json` stayed beside the original. Earned 2026-07-30 in christofuturism,
    where re-scaffolding a lookbook stranded the provenance of 8 of 12 exemplars.
    """
    try:
        return os.path.getsize(a) == os.path.getsize(b) and _sha256(a) == _sha256(b)
    except OSError:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--id", required=True); ap.add_argument("--name", required=True)
    ap.add_argument("--anchor", default=None,
                    help="REQUIRED unless --from-explore, where it defaults to the first pick")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--style-line", required=True)
    ap.add_argument("--palette-ground", default=""); ap.add_argument("--palette-fill", default=""); ap.add_argument("--palette-line", default="")
    ap.add_argument("--reject", action="append", default=[])
    ap.add_argument("--gate", action="append", default=[])
    ap.add_argument("--max-elements", type=int, default=5)
    # REQUIRED, like --gate and for the same reason (gap G41, #44). SPEC 4.7 has said since
    # v0.12 that textPolicy is REQUIRED on new packs, and this scaffolder could not write it,
    # so the pre-v0.12 fallback ("absent reads as diegetic") silently applied to packs written
    # long after it: pov-fine-screen-halftone's gate says NO GLYPH ANYWHERE while its manifest
    # silence let in-world text through. A pack that cannot say whether glyphs are allowed is
    # not finished.
    ap.add_argument("--text-policy", dest="text_policy", default=None,
                    choices=("none", "diegetic", "furniture"),
                    help="REQUIRED (SPEC 4.7 v0.12): none = no glyphs at all; diegetic = text "
                         "that exists in the depicted world; furniture = diegetic plus the "
                         "image's own explanatory chrome (title bar, panel captions)")
    ap.add_argument("--require-entity", action="append", default=[], metavar="ID",
                    help="Canon entity id this pack's law depends on (e.g. north-star-cross). "
                         "generate.py refuses a render in the pack that does not bind it.")
    # FROM AN EXPLORE PICK, and the decision behind it (SPEC v0.62, #60).
    ap.add_argument("--from-explore", action="append", default=[], metavar="DIR",
                    help="an explore output dir (or a folder of them, one per subject); "
                         "with --pick, promotes the picked roll of each as a ref")
    ap.add_argument("--pick", default=None, metavar="ID", help="the explore direction picked")
    ap.add_argument("--decided-by", default=None, help="who picked / decided the scope")
    ap.add_argument("--decided-on", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--verbatim", action="append", default=[],
                    help="their words, verbatim (repeatable); recorded with the decision")
    ap.add_argument("--scope-use", action="append", default=[], metavar="ID",
                    help="a use this pack may render for (repeatable); writes a TYPED scope "
                         "that generate.py enforces with --use")
    ap.add_argument("--scope-subjects", default=None, help="who or what the pack may depict")
    ap.add_argument("--scope-never", action="append", default=[],
                    help="what it must never depict (repeatable)")
    a = ap.parse_args()

    decided_on = a.decided_on or datetime.date.today().isoformat()
    try:
        datetime.date.fromisoformat(decided_on)
    except ValueError:
        sys.exit(f"scaffold: --decided-on {decided_on!r} is not YYYY-MM-DD")
    if (a.from_explore or a.pick) and not (a.from_explore and a.pick):
        sys.exit("scaffold: --from-explore and --pick go together (which runs, which direction)")
    if a.from_explore and not a.decided_by:
        sys.exit("scaffold: a pick needs --decided-by (who picked). The promoted refs are "
                 "blessed in their name, and a blessing with nobody behind it is not one.")
    if a.scope_use and not (a.decided_by and a.verbatim):
        sys.exit("scaffold: --scope-use needs --decided-by and --verbatim: a scope is a "
                 "decision, recorded as who, when and their words (SPEC v0.62).")
    picked, considered, named = [], [], {}
    if a.from_explore:
        picked, considered = explore_picks(a.from_explore, a.pick)
        named = {os.path.abspath(src): dest for src, dest in picked}
        if not a.anchor:
            a.anchor = picked[0][0]
    if not a.anchor:
        sys.exit("scaffold: --anchor is required (or --from-explore with --pick)")
    a.ref = [src for src, _ in picked] + a.ref

    if not a.gate:
        sys.exit("scaffold: a Style Pack MUST have >=1 --gate assertion (a gateless pack is a mood board)")
    if not a.text_policy:
        sys.exit("scaffold: a Style Pack MUST declare --text-policy none|diegetic|furniture "
                 "(SPEC 4.7). Silence reads as 'diegetic', a fallback written for pre-v0.12 packs; "
                 "if the gate forbids every glyph, the policy is 'none'.")

    pack = os.path.abspath(a.dir)
    refs_dir = os.path.join(pack, "refs")
    os.makedirs(refs_dir, exist_ok=True)

    # anchor is always a ref; de-dup by source path, preserve order (anchor first)
    src_list, seen = [], set()
    for p in [a.anchor] + a.ref:
        ap_ = os.path.abspath(os.path.expanduser(p))
        if not os.path.exists(ap_): sys.exit(f"scaffold: ref not found: {ap_}")
        if ap_ in seen: continue
        seen.add(ap_); src_list.append(ap_)
    if not (3 <= len(src_list) <= 8):
        sys.exit(f"scaffold: need 3-8 refs total (got {len(src_list)}); the look is the references")

    ref_rel = []
    anchor_rel = None
    unprovenanced = []
    promoted = {}
    for i, src in enumerate(src_list):
        base = named.get(src) or os.path.basename(src)
        # keep basenames unique inside the pack
        dest = os.path.join(refs_dir, base)
        n = 1
        while (os.path.exists(dest) and os.path.abspath(dest) != src
               and not _same_bytes(dest, src)):
            stem, ext = os.path.splitext(base); dest = os.path.join(refs_dir, f"{stem}-{n}{ext}"); n += 1
        if os.path.abspath(dest) != src:
            shutil.copy2(src, dest)
            # CARRY THE PROVENANCE WITH THE REF.
            # generate.py writes `<image>.recipe.json` beside every render, and copying
            # the image alone strands it: the pack ends up holding art that nothing can
            # account for. That is worse than an obviously-missing recipe, because
            # `universe-doctor` EXCLUDES style-pack refs from its provenance sweep on the
            # assumption the manifest covers them, so an unprovenanced pack scored a clean
            # 10/10 (gary-sheng-art, 2026-07-27) and the gap was only found by a human
            # asking "where's the style provenance?". Both packs were then fixed by hand
            # and the scaffolder was left to do it again, which it did.
            sidecar = src + ".recipe.json"
            if os.path.exists(sidecar):
                shutil.copy2(sidecar, dest + ".recipe.json")
            else:
                unprovenanced.append(base)
            # CARRY A BLESSING WITH THE REF TOO (v0.41). `bless_ref.py` records that a
            # named human approved these exact bytes; leaving the marker behind at the
            # source turns an approved ref back into an anonymous candidate on the way
            # into the pack, and a pack rebuild is a ONE-COMMAND operation people run
            # often. Same reasoning as the recipe above: the sidecar is part of the ref.
            blessing = src + ".blessed.json"
            if os.path.exists(blessing):
                shutil.copy2(blessing, dest + ".blessed.json")
        rel = os.path.relpath(dest, pack)
        ref_rel.append(rel)
        if src in named:
            promoted[rel] = src
        if i == 0: anchor_rel = rel

    palette = {}
    if a.palette_ground: palette["ground"] = [c.strip() for c in a.palette_ground.split(",") if c.strip()]
    if a.palette_fill:   palette["fill"]   = [c.strip() for c in a.palette_fill.split(",") if c.strip()]
    if a.palette_line:   palette["line"]   = [c.strip() for c in a.palette_line.split(",") if c.strip()]

    manifest = {
        "id": a.id, "name": a.name,
        "anchor": anchor_rel,
        "refs": ref_rel,
        "palette": palette,
        "styleLine": a.style_line,
        "rejectedPoles": a.reject,
        "gate": a.gate,
        "textPolicy": a.text_policy,
        "maxElements": a.max_elements,
        **({"requiredEntities": [x.strip() for x in a.require_entity if x.strip()]} if a.require_entity else {}),
    }
    decided = {"by": a.decided_by, "on": decided_on, "verbatim": list(a.verbatim)}
    if a.scope_use:
        manifest["scope"] = {"uses": list(dict.fromkeys(a.scope_use)),
                             **({"subjects": a.scope_subjects} if a.scope_subjects else {}),
                             **({"never": list(a.scope_never)} if a.scope_never else {}),
                             "decided": decided}
    if promoted:
        manifest["promotedFrom"] = {
            "explore": [os.path.relpath(os.path.abspath(os.path.expanduser(d)), pack)
                        for d in a.from_explore],
            "pick": a.pick, "considered": considered, "decided": decided,
            "refs": {r: os.path.relpath(s, pack) for r, s in promoted.items()}}
    with open(os.path.join(pack, "pack.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # validate: every ref resolves, anchor is in refs
    for r in ref_rel:
        if not os.path.exists(os.path.join(pack, r)): sys.exit(f"scaffold: ref did not land: {r}")
    if anchor_rel not in ref_rel: sys.exit("scaffold: anchor must be one of refs")

    # THE PICK IS A BLESSING. Whoever picked looked at these exact bytes and chose them, so
    # each promoted ref is blessed in their name through bless_ref's own writer (bound to the
    # sha256). A rebuild over the same bytes keeps the existing blessing; changed bytes
    # replace it, keeping the previous approver under `replaced`.
    if promoted:
        by = f"{a.decided_by}, {decided_on}"
        words = "; ".join(f"'{v}'" for v in a.verbatim)
        note = (f"picked explore direction {a.pick!r}" + (f" ({words})" if words else "")
                + (f" over {', '.join(c for c in considered if c != a.pick)}"
                   if len(considered) > 1 else ""))
        for rel in promoted:
            state, _m = bless_ref.state_of(pack, rel)
            if state == "blessed":
                continue
            bless_ref.cmd_bless(pack, manifest, rel, by, note, rebless=state != "unblessed")
    if unprovenanced:
        print(f"  WARNING: {len(unprovenanced)} ref(s) copied with NO recipe sidecar: "
              f"{', '.join(unprovenanced)}. These are un-auditable: no divergence check can\n"
              f"  ever run against them, and universe-doctor skips pack refs when scoring\n"
              f"  provenance, so nothing downstream will flag this for you. Prefer refs made\n"
              f"  by generate.py, which writes <image>.recipe.json beside every render.")
    print(f"[style-pack] OK  {a.id}  ({len(ref_rel)} refs, {len(a.gate)} gate assertions)  -> {pack}/pack.json")

    # BLESSING COVERAGE (v0.41). The skill says "only images a human approved", and for
    # every pack before this one that claim lived in somebody's prose. A pack whose refs
    # are mostly unreviewed candidates is a normal and honest state; SILENTLY reporting it
    # as blessed is not. Printed here, at the end of the run the operator is watching,
    # because a catalog read at session start loses to a line read at the point of use.
    blessed = sum(1 for r in ref_rel if os.path.exists(os.path.join(pack, r + ".blessed.json")))
    print(f"[style-pack] blessing coverage: {blessed} of {len(ref_rel)} refs individually blessed.")
    if blessed < len(ref_rel):
        anchor_note = ("  The ANCHOR is unblessed, and it is passed FIRST on every render "
                       "this pack makes.\n"
                       if not os.path.exists(os.path.join(pack, anchor_rel + ".blessed.json")) else "")
        print(f"  The rest are CANDIDATES, not approvals. Say so when you report this pack.\n"
              f"{anchor_note}"
              f"  Record one:  bless_ref.py {pack} --ref <name> --by \"<who, when>\"\n"
              f"  See them all: bless_ref.py {pack} --status")

if __name__ == "__main__":
    main()
