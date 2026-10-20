import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
const CLI = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../../engine/agenticstory/cli.py"), "utf8");
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
  assert.match(body, /wait \$pa/);
  assert.match(body, /ask_operator\(\{ kind: "compare"/);
});

test("nothing is golden before their yes", () => {
  assert.match(body, /Nothing is golden before that yes/);
  assert.match(body, /Never choose for them/);
});

test("on yes: init, seed with the fixed direction, board and mark, private repo, path", () => {
  assert.match(body, /abu init/);
  assert.match(body, /abu seed[\s\S]*\.fixed\.json/);
  assert.match(body, /gh repo create <owner>\/<slug>-universe --private/);
  assert.match(body, /Return the universe path/);
});

test("a thin site is said plainly", () => {
  assert.match(body, /A thin read[\s\S]*say so plainly/);
});

test("billing is not mentioned at all, so nothing claims to automate it", () => {
  assert.doesNotMatch(skill, /billing|invoice/i);
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

test("the kept-site route is runnable: the exact command, and it becomes direction 1 of 3", () => {
  assert.match(body, /node "\$SK\/read-site\.mjs" <url> --out <work>\/site --direction <work>\/a\.json/);
  assert.match(body, /direction 1 of the 3/);
  assert.match(body, /For the "not really the brand" answer, omit `--direction`/);
});

test("paths resolve from anywhere: ABU is located the make-a-book way and abu has an invocation", () => {
  assert.match(body, /ABU=\$\(python3 -c "import agenticstory,pathlib;/);
  assert.match(body, /abu\(\) \{ node "\$ABU\/bin\/abu\.mjs"/);
  for (const t of ["<work>", "<repos>", "<owner>", "<slug>"]) assert.ok(body.includes(`**\`${t}\`**`), t + " is defined");
  assert.doesNotMatch(body, /node skills\/explore-a-personal-brand/);
});

test("every script the skill runs exists, and every abu flag it uses is in the engine CLI", () => {
  for (const m of body.matchAll(/"\$SK\/([\w.-]+)"/g)) assert.ok(existsSync(join(ROOT, "scripts", m[1])), m[1]);
  assert.ok(existsSync(join(ROOT, "../../bin/abu.mjs")));
  for (const f of ["--from", "--brief", "--mark", "--board", "--name"]) {
    assert.ok(body.includes(f) && CLI.includes(`"${f}"`), f);
  }
  assert.match(CLI, /sub\.add_parser\("seed"/);
});

test("failure handling: each has its action", () => {
  assert.match(body, /HTTP error, a redirect to a login page, or an unreachable host[\s\S]*go to the interview/);
  assert.match(body, /at most the name and one color the operator confirms/);
  assert.match(body, /If the compare page is unavailable[\s\S]*AskUserQuestion[\s\S]*Never proceed on silence/);
  assert.match(body, /If `gh` is missing, unauthenticated or the name is taken[\s\S]*valid and\s+safe locally/);
  assert.match(body, /failed board is re-rendered once on its own, then reported/);
  assert.match(body, /A raster logo only[\s\S]*monogram[\s\S]*potracer/);
  assert.match(body, /Offline: say so and stop/);
});
