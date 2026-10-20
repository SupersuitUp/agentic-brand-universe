// JS mirror of engine/agenticstory/direction.py validate_direction. Keep the two in step.
export const HEX = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

export function validateDirection(d) {
  const errs = [];
  if (!d || typeof d !== "object" || Array.isArray(d)) return ["direction must be an object"];
  if (typeof d.name !== "string" || !d.name.trim()) errs.push("name: required non-empty string");
  let pal = d.palette;
  if (!pal || typeof pal !== "object") { errs.push("palette: required object"); pal = {}; }
  for (const k of ["ground", "ink", "accent"]) if (!(k in pal)) errs.push(`palette.${k}: required`);
  for (const k of ["ground", "ink", "accent", "lightGround", "lightInk", "lightAccent"]) {
    if (k in pal && !(typeof pal[k] === "string" && HEX.test(pal[k]))) errs.push(`palette.${k}: not a hex color: ${JSON.stringify(pal[k])}`);
  }
  let t = d.type;
  if (!t || typeof t !== "object") { errs.push("type: required object"); t = {}; }
  for (const k of ["display", "body"]) if (typeof t[k] !== "string" || !t[k].trim()) errs.push(`type.${k}: required non-empty font family`);
  const m = d.mark;
  if (!m || typeof m !== "object") errs.push("mark: required object");
  else if (m.kind === "monogram") { if (typeof m.letters !== "string" || !m.letters.trim()) errs.push("mark.letters: required for a monogram"); }
  else if (m.kind === "svg") { if (typeof m.svg !== "string" || !m.svg.includes("<svg")) errs.push("mark.svg: required SVG text for kind svg"); }
  else errs.push(`mark.kind: must be monogram or svg, got ${JSON.stringify(m.kind)}`);
  return errs;
}
