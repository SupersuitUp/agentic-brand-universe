#!/usr/bin/env node
// `abu`, from npm (@supersuit/abu): the Agentic Brand Universe engine, which is Python, run from
// the copy inside this package. The package version IS the engine version (the Claude plugin's
// version, released together), so a repo that pins @supersuit/abu pins exactly which gate it runs.
//
// It needs python3 >= 3.9 (every Mac has one; so does Vercel's build image). ABU_PYTHON names
// another interpreter. Nothing is installed into Python: the engine runs off PYTHONPATH.
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const engine = join(dirname(fileURLToPath(import.meta.url)), "..", "engine");
const python = process.env.ABU_PYTHON || "python3";
const env = { ...process.env, PYTHONPATH: [engine, process.env.PYTHONPATH].filter(Boolean).join(":") };
const r = spawnSync(python, ["-m", "agenticstory.cli", ...process.argv.slice(2)], { stdio: "inherit", env });
if (r.error) {
  console.error(`abu: could not run ${python} (${r.error.code ?? r.error.message}). ABU's engine is Python: install python3 3.9 or later, or set ABU_PYTHON.`);
  process.exit(127);
}
process.exit(r.status ?? 1);
