import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync, mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
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
  assert.match(body, /ABU=\$\{CLAUDE_PLUGIN_ROOT:-\$\(ls -d/);
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

test("the emit check runs through the Supersuit resolver, never a preview path", () => {
  assert.match(body, /~\/\.freedom\/bin\/freedom-lib run \.agents\/lib\/freedom-brand\.mjs emit --universe "\$U" --surface artifact/);
  assert.match(body, /freedom-lib` is\s+missing, say Supersuit is not installed and skip only the emit check, never the universe/);
  assert.ok(!skill.includes(".freedom/preview"));
});

test("setup: shell state does not persist, so every block that needs it re-sources setup.sh", () => {
  assert.match(body, /Shell state does not persist between tool calls/);
  const blocks = [...body.matchAll(/```bash\n([\s\S]*?)```/g)].map((m) => m[1]);
  const using = blocks.filter((b) => /\$SK|\babu \w|\$ABU/.test(b) && !b.includes("cat > <work>/setup.sh"));
  assert.ok(using.length >= 3);
  for (const b of using) assert.ok(b.startsWith(". <work>/setup.sh || exit 1\n"), b.slice(0, 60));
});


// The setup snippet, run for real: from /tmp, with HOME pointing at a fake plugin cache named like
// the marketplace (.claude-plugin/marketplace.json "name"), never like the author.
const SETUP = body.match(/<<'SETUP'\n([\s\S]*?)\nSETUP/)[1];
const MARKET = JSON.parse(readFileSync(join(ROOT, "../../.claude-plugin/marketplace.json"), "utf8")).name;
function runSetup({ versions, pluginRoot }) {
  const home = mkdtempSync(join(tmpdir(), "fakehome-"));
  for (const v of versions) {
    const d = join(home, ".claude/plugins/cache", MARKET, "abu", v, "skills/explore-a-personal-brand/scripts");
    mkdirSync(d, { recursive: true }); writeFileSync(join(d, "read-site.mjs"), "// fake");
    mkdirSync(join(home, ".claude/plugins/cache", MARKET, "abu", v, "bin"), { recursive: true });
    writeFileSync(join(home, ".claude/plugins/cache", MARKET, "abu", v, "bin/abu.mjs"), "// fake");
  }
  const f = join(home, "setup.sh"); writeFileSync(f, SETUP);
  const env = { PATH: process.env.PATH, HOME: home, ...(pluginRoot ? { CLAUDE_PLUGIN_ROOT: pluginRoot } : {}) };
  const r = spawnSync("bash", ["-c", `. ${f} || exit 7; echo "$SK"`], { cwd: "/tmp", env, encoding: "utf8" });
  return { ...r, home };
}

test("setup finds the NEWEST cached ABU from any directory", () => {
  const r = runSetup({ versions: ["1.9.0", "1.10.0", "1.2.0"] });
  assert.equal(r.status, 0, r.stderr);
  const sk = r.stdout.trim();
  assert.ok(sk.includes("/abu/1.10.0/"), sk);
  assert.ok(existsSync(join(sk, "read-site.mjs")));
});

test("setup prefers CLAUDE_PLUGIN_ROOT when set", () => {
  const root = mkdtempSync(join(tmpdir(), "root-"));
  mkdirSync(join(root, "bin")); writeFileSync(join(root, "bin/abu.mjs"), "// fake");
  const r = runSetup({ versions: ["1.9.0"], pluginRoot: root });
  assert.equal(r.status, 0, r.stderr);
  assert.ok(r.stdout.trim().startsWith(root));
});

test("setup with no ABU installed stops the calling block and points at abu:onboard", () => {
  const r = runSetup({ versions: [] });
  assert.notEqual(r.status, 0);
  assert.equal(r.status, 7, "the sourcing block's `|| exit 1` path is reached");
  assert.match(r.stdout + r.stderr, /abu:onboard/);
});

test("make-a-book, book-doctor and land-work use the same corrected discovery", () => {
  for (const sk of ["make-a-book", "book-doctor", "land-work"]) {
    const t = readFileSync(join(ROOT, "..", sk, "SKILL.md"), "utf8");
    assert.ok(t.includes("${CLAUDE_PLUGIN_ROOT:-$(ls -d ~/.claude/plugins/cache/*/abu/*/ 2>/dev/null | sort -V | tail -1)}"), sk);
    assert.ok(!t.includes("cache/garysheng"), sk);
  }
  assert.ok(!skill.includes("cache/garysheng"));
});
