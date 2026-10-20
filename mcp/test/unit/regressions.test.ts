// Regressions from the independent review of PR #88 (findings 1, 2, 5, 6, 7, 8, 11, 12).
import { test } from "node:test";
import assert from "node:assert/strict";
import { TEST_RING } from "../helpers.ts";
import { runTool } from "../../src/server.ts";
import { TOOLS } from "../../src/tools/index.ts";
import { memoryLimiter } from "../../src/ratelimit.ts";
import { parseTestSummary } from "../../src/evidence/parsers.ts";
import { recommendFlowModel } from "../../src/advisor/index.ts";
import { SNAPSHOT } from "../../src/advisor/snapshot.ts";
import { RISKS } from "../../src/rules/levels.ts";
import type { ToolContext } from "../../src/tools/common.ts";

const ctx: ToolContext = { ring: TEST_RING, now: () => Math.floor(Date.now() / 1000), limiter: memoryLimiter(1e9) };
async function call(name: string, args: unknown) {
  const r = await runTool(TOOLS.find((t) => t.name === name)!, args, ctx);
  return { json: JSON.parse(r.content[0]!.text), isError: r.isError === true, bytes: Buffer.byteLength(r.content[0]!.text) };
}
const PASS = "============================== 3 passed in 0.10s ==============================";
const FAIL = "============================== 1 failed, 2 passed in 0.10s ==============================";
const SHA = (c: string) => c.repeat(64);

async function contract(dod: Array<{ text: string; proof: string }>) {
  return (await call("start_flow_task", { outcome: "regression", dod })).json.token as string;
}

test("finding 1: a failing rerun with contradictory counts invalidates the earlier pass and blocks DONE", async () => {
  let token = await contract([{ text: "pytest passes", proof: "test" }]);
  token = (await call("check_flow_evidence", { token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest", exit: 0, out: PASS }] })).json.token;
  assert.equal((await call("check_flow_done", { token })).json.verdict, "DONE");
  const rerun = await call("check_flow_evidence", { token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest", exit: 1, out: FAIL, failed: 0 }] });
  assert.equal(rerun.json.results[0].code, "COUNTS_MISMATCH");
  assert.deepEqual(rerun.json.open, ["AC01"]);
  const done = await call("check_flow_done", { token: rerun.json.token });
  assert.equal(done.json.verdict, "NOT_DONE");
  assert.match(done.json.missing[0].need, /last record failed/);
});

test("finding 1: exit 0 with a failing summary also invalidates an earlier pass", async () => {
  let token = await contract([{ text: "pytest passes", proof: "test" }]);
  token = (await call("check_flow_evidence", { token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest", exit: 0, out: PASS }] })).json.token;
  const rerun = await call("check_flow_evidence", { token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest", exit: 0, out: FAIL }] });
  assert.equal(rerun.json.results[0].code, "EXIT_OUTPUT_CONFLICT");
  assert.equal((await call("check_flow_done", { token: rerun.json.token })).json.verdict, "NOT_DONE");
  const fixed = await call("check_flow_evidence", { token: rerun.json.token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest", exit: 0, out: PASS }] });
  assert.equal((await call("check_flow_done", { token: fixed.json.token })).json.verdict, "DONE", "a later consistent pass accepts again");
});

test("finding 2: zero passed tests never count (unittest all skipped, phpunit all skipped)", async () => {
  assert.equal(parseTestSummary("Ran 1 test in 0.001s\n\nOK (skipped=1)")?.passed, 0);
  assert.equal(parseTestSummary("Ran 4 tests in 0.010s\n\nOK (skipped=1)")?.passed, 3);
  assert.equal(parseTestSummary("Ran 3 tests in 0.010s\n\nFAILED (failures=1, skipped=2)")?.passed, 0);
  assert.equal(parseTestSummary("OK, but incomplete, skipped, or risky tests!\nTests: 3, Assertions: 0, Skipped: 3.")?.passed, 0);
  const token = await contract([{ text: "unit tests pass", proof: "test" }]);
  const ev = await call("check_flow_evidence", { token, evidence: [{ item: "AC01", kind: "test", cmd: "python -m unittest", exit: 0, out: "Ran 1 test in 0.001s\n\nOK (skipped=1)" }] });
  assert.equal(ev.json.results[0].code, "NO_TESTS_RAN");
  assert.equal((await call("check_flow_done", { token: ev.json.token })).json.verdict, "NOT_DONE");
});

test("finding 5: `src/./a.ts` and `src/a.ts` are one file for staleness", async () => {
  let token = await contract([{ text: "pytest passes", proof: "test" }, { text: "src/a.ts changed", proof: "file" }]);
  token = (await call("check_flow_evidence", { token, evidence: [
    { item: "AC01", kind: "test", cmd: "pytest", exit: 0, out: PASS },
    { item: "AC02", kind: "file", path: "src/a.ts", sha256: SHA("1") },
  ] })).json.token;
  const changed = await call("check_flow_evidence", { token, evidence: [{ item: "AC02", kind: "file", path: "src/./a.ts", sha256: SHA("2") }] });
  assert.deepEqual(changed.json.stale, ["AC01"]);
  assert.equal((await call("check_flow_done", { token: changed.json.token })).json.verdict, "NOT_DONE");
  const dotdot = await call("check_flow_evidence", { token, evidence: [{ item: "AC02", kind: "file", path: "src/./../a.ts", sha256: SHA("3") }] });
  assert.equal(dotdot.json.results[0].code, "BAD_PATH");
});

test("finding 6: blank cmd or path is not evidence", async () => {
  const token = await contract([{ text: "build command succeeds", proof: "command" }, { text: "notes.md updated", proof: "file" }]);
  const ev = await call("check_flow_evidence", { token, evidence: [
    { item: "AC01", kind: "command", cmd: "   ", exit: 0, out: "" },
    { item: "AC02", kind: "file", path: " ", sha256: SHA("4") },
  ] });
  assert.deepEqual(ev.json.results.map((r: { code: string }) => r.code), ["MISSING_FIELD", "MISSING_FIELD"]);
  assert.equal((await call("check_flow_done", { token: ev.json.token })).json.verdict, "NOT_DONE");
});

const FRESH = new Date(Date.parse(SNAPSHOT.fetched_at) + 3600_000);

test("finding 7: a qualified route ID keeps its provider restriction", () => {
  const out = recommendFlowModel({ task: "writing", have: ["github-copilot/gpt-6.1-sol"] }, FRESH) as { shortlist: Array<{ model: string }> };
  for (const e of out.shortlist) assert.doesNotMatch(e.model, /^openai\//, JSON.stringify(out.shortlist));
});

test("findings 8 and 11: past the website's 14-day expiry the advisor refuses, in fields trimming cannot remove", () => {
  const fetched = Date.parse(SNAPSHOT.fetched_at);
  const okay = recommendFlowModel({ task: "writing" }, new Date(fetched + 13 * 86400_000)) as Record<string, any>;
  assert.equal(okay.expired, false);
  assert.ok(okay.shortlist.length > 0);
  const late = new Date(fetched + 15 * 86400_000);
  const many = Array.from({ length: 30 }, (_, i) => (i % 2 ? `unknown-model-${i}` : SNAPSHOT.models[i % SNAPSHOT.models.length]!.id));
  for (const input of [{ task: "writing" }, { task: "writing", have: many }]) {
    const out = recommendFlowModel(input, late) as Record<string, any>;
    assert.equal(out.expired, true);
    assert.deepEqual(out.shortlist, []);
    assert.equal(out.expires, new Date(fetched + 14 * 86400_000).toISOString().slice(0, 10));
    assert.ok(Buffer.byteLength(JSON.stringify(out)) <= 1500);
  }
});

test("finding 12: a valid maximum-size contract succeeds within the budget", async () => {
  // Worst case: every item linted, all modules and gates, the version note and no non-goals.
  const dod = Array.from({ length: 10 }, () => ({ text: "works", proof: "url", level: "production" }));
  const r = await call("start_flow_task", { outcome: "o".repeat(300), dod, risks: [...RISKS], local_flow: "1.0.0" });
  assert.equal(r.isError, false, JSON.stringify(r.json).slice(0, 200));
  assert.match(r.json.token, /^nbf1\./);
  assert.ok(r.bytes <= 1500, String(r.bytes));
});
