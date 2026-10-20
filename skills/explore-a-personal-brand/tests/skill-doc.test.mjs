import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const skill = readFileSync(join(ROOT, "SKILL.md"), "utf8");
const body = skill.replace(/^---[\s\S]*?---/, "");
const plugin = JSON.parse(readFileSync(join(ROOT, "../../.claude-plugin/plugin.json"), "utf8"));

test("frontmatter names the skill and says when to use it", () => {
  assert.match(skill, /^---\nname: explore-a-personal-brand\ndescription: .*Use when/);
});

test("the starting question has exactly three answers, worded with the operator's name", () => {
  assert.match(body, /<Name>'s site is the brand/);
  assert.match(body, /<Name> has a site, but it is not really the brand/);
  assert.match(body, /<Name> does not have one yet \(default\)/);
  assert.match(body, /exactly three answers/);
  assert.match(body, /never "you", never "I"/);
});

test("profile first, never ask what the workspace knows", () => {
  assert.match(body, /Read the operator's profile/);
  assert.match(body, /Never ask what the profile already answers/);
});

test("the interview goes through freedom:interview-me with the five questions", () => {
  assert.match(body, /freedom:interview-me/);
  for (const q of ["Who are the pages for", "Three words a reader should feel", "Looks they admire", "never want to look like", "already theirs"]) {
    assert.ok(body.includes(q), q);
  }
  assert.match(body, /Stop as soon as three distinct directions can be named/);
});

test("three directions that differ in concept, a kept site is one of them", () => {
  assert.match(body, /three `direction\.json` files/i);
  assert.match(body, /differ in concept, not in palette alone/);
  assert.match(body, /kept site becomes \*\*one of the three\*\*/);
});

test("boards render in parallel and go to a compare page", () => {
  assert.match(body, /render-board\.mjs/);
  assert.match(body, /wait\n/);
  assert.match(body, /ask_operator\(\{ kind: "compare"/);
});

test("nothing is golden before their yes", () => {
  assert.match(body, /Nothing is golden before that yes/);
  assert.match(body, /Never choose for them/);
});

test("on yes: init, seed with the fixed direction, board and mark, private repo, path", () => {
  assert.match(body, /abu init/);
  assert.match(body, /abu seed[\s\S]*\.fixed\.json[\s\S]*\.mark\.svg[\s\S]*--board/);
  assert.match(body, /gh repo create <owner>\/<slug>-universe --private/);
  assert.match(body, /Return the universe path/);
});

test("a thin site is said plainly", () => {
  assert.match(body, /Say plainly when a site is thin/);
});

test("billing is not mentioned at all, so nothing claims to automate it", () => {
  assert.doesNotMatch(skill, /billing|invoice|payment/i);
});

test("HDSOP exists and every script the skill names exists", () => {
  assert.ok(existsSync(join(ROOT, "HDSOP.md")));
  for (const f of ["read-site.mjs", "render-board.mjs", "contrast.mjs", "mark.mjs", "fonts.mjs", "glyph-paths.py", "cdp.mjs"]) {
    assert.ok(existsSync(join(ROOT, "scripts", f)), f);
  }
});

test("the plugin description lists the skill so it ships with a name", () => {
  assert.match(plugin.description, /explore-a-personal-brand/);
});
