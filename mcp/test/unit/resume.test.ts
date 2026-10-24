// get_flow_step with event resume: the goal-file block comes from the contract token alone.
import { test } from "node:test";
import assert from "node:assert/strict";
import { TEST_RING } from "../helpers.ts";
import { runTool } from "../../src/server.ts";
import { TOOLS } from "../../src/tools/index.ts";
import { memoryLimiter } from "../../src/ratelimit.ts";
import { getCard, FLOW_VERSION } from "../../src/content/cards.ts";
import { CONTRACT_PREFIX, LIFETIME_S, MAX_AGE_S, decodeToken } from "../../src/token.ts";
import type { ToolContext } from "../../src/tools/common.ts";

const DAY = 86_400;
const T0 = 1_800_000_000;
let clock = T0;
const ctx: ToolContext = { ring: TEST_RING, now: () => clock, limiter: memoryLimiter(1e9) };
async function call(name: string, args: unknown) {
  const r = await runTool(TOOLS.find((t) => t.name === name)!, args, ctx);
  const text = r.content[0]!.text;
  return { text, json: JSON.parse(text), isError: r.isError === true };
}
const PASS = "============================== 3 passed in 0.10s ==============================";
const FAIL = "============================== 1 failed, 2 passed in 0.10s ==============================";
const date = (unix: number) => new Date(unix * 1000).toISOString().slice(0, 10);

/** Split the block into its fields; DOD rows are returned in order. */
function parse(block: string) {
  const lines = block.split("\n");
  const field = (name: string) => lines.find((l) => l.startsWith(`${name}: `))?.slice(name.length + 2);
  return {
    lines,
    goalId: field("GOAL_ID"),
    rows: lines.filter((l) => l.startsWith("- AC")),
    status: field("STATUS"),
    checkpoint: field("CHECKPOINT"),
    next: field("NEXT_SAFE_ACTION"),
    contract: field("FLOW_CONTRACT") ?? "",
  };
}

async function resume(token: string) {
  const r = await call("get_flow_step", { token, event: "resume" });
  assert.equal(r.isError, false, r.text.slice(0, 200));
  return { ...r, block: parse(r.json.goal_block as string) };
}

test("resume with a token returns a goal block matching the contract and item statuses", async () => {
  clock = T0;
  const start = await call("start_flow_task", { outcome: "parser fixed", dod: [
    { text: "pytest passes", proof: "test" }, { text: "CHANGELOG.md entry", proof: "file" },
    { text: "page is live", proof: "url", level: "production" }, { text: "owner approves the copy", proof: "observation" },
  ] });
  const ev = await call("check_flow_evidence", { token: start.json.token, evidence: [
    { item: "AC01", kind: "test", cmd: "pytest", exit: 0, out: PASS },
    { item: "AC02", kind: "file", path: "CHANGELOG.md", sha256: "a".repeat(64) },
    { item: "AC03", kind: "url", url: "https://example.com/parser", status: 503 },
  ] });
  clock = T0 + 5 * DAY;
  const r = await resume(ev.json.token);
  assert.equal(r.json.card, "event:resume");
  assert.equal(r.json.flow_version, FLOW_VERSION);
  assert.deepEqual(r.json.rules, getCard("event:resume")!.rules.slice(0, 2));
  assert.equal(r.json.source, getCard("event:resume")!.source);
  const b = r.block;
  assert.equal(b.goalId, `flow-${start.json.contract}`);
  assert.equal(b.lines[0], `GOAL_ID: flow-${start.json.contract}`);
  assert.match(b.lines[1]!, /^OUTCOME: <.+>$/);
  assert.match(b.lines[2]!, /^NON_GOALS: <.+>$/);
  assert.match(b.lines[3]!, /^DOD: <.+>$/);
  assert.deepEqual(b.rows, [
    "- AC01 test, local: ACCEPTED",
    "- AC02 file, static: ACCEPTED",
    "- AC03 url, production: FAILED",
    "- AC04 observation, user: OPEN",
  ]);
  assert.equal(b.status, "ACTIVE");
  assert.equal(b.checkpoint, `2 of 4 accepted, contract expires ${date(clock + LIFETIME_S)}`);
  assert.match(b.next!, /check_flow_evidence/);
  assert.equal(b.lines.at(-1), `FLOW_CONTRACT: ${b.contract}`);
  // The block's contract is the renewed token: same contract, same item state, usable by the next tool.
  const renewed = decodeToken(b.contract, CONTRACT_PREFIX, TEST_RING, clock);
  assert.equal(renewed.contract.subarray(0, 4).toString("hex"), start.json.contract);
  assert.equal(renewed.expires, clock + LIFETIME_S);
  assert.deepEqual(renewed.items.map((i) => i.status), ["ACCEPTED", "ACCEPTED", "FAILED", "OPEN"]);
  const done = await call("check_flow_done", { token: b.contract });
  assert.equal(done.json.verdict, "NOT_DONE");
  assert.deepEqual(done.json.missing.map((m: { item: string }) => m.item), ["AC03", "AC04"]);
});

test("resume marks a run made stale by a later file change and counts only current items", async () => {
  clock = T0;
  let token = (await call("start_flow_task", { outcome: "x", dod: [{ text: "pytest passes", proof: "test" }, { text: "src/a.ts changed", proof: "file" }] })).json.token;
  token = (await call("check_flow_evidence", { token, evidence: [
    { item: "AC01", kind: "test", cmd: "pytest", exit: 0, out: PASS }, { item: "AC02", kind: "file", path: "src/a.ts", sha256: "1".repeat(64) },
  ] })).json.token;
  token = (await call("check_flow_evidence", { token, evidence: [{ item: "AC02", kind: "file", path: "src/a.ts", sha256: "2".repeat(64) }] })).json.token;
  const b = (await resume(token)).block;
  assert.deepEqual(b.rows, ["- AC01 test, local: STALE", "- AC02 file, static: ACCEPTED"]);
  assert.match(b.checkpoint!, /^1 of 2 accepted,/);
  assert.match(b.next!, /check_flow_evidence/);
});

test("NEXT_SAFE_ACTION follows the token state: open work, done gate, repeated failure", async () => {
  clock = T0;
  let token = (await call("start_flow_task", { outcome: "x", dod: [{ text: "pytest passes", proof: "test" }] })).json.token;
  const fresh = (await resume(token)).block;
  assert.deepEqual(fresh.rows, ["- AC01 test, local: OPEN"]);
  assert.match(fresh.checkpoint!, /^0 of 1 accepted,/);
  assert.match(fresh.next!, /check_flow_evidence/);
  const passed = (await call("check_flow_evidence", { token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest", exit: 0, out: PASS }] })).json.token;
  const ready = (await resume(passed)).block;
  assert.match(ready.checkpoint!, /^1 of 1 accepted,/);
  assert.equal(ready.next, "call check_flow_done");
  for (let i = 0; i < 2; i++) {
    token = (await call("check_flow_evidence", { token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest", exit: 1, out: FAIL }] })).json.token;
  }
  const stuck = (await resume(token)).block;
  assert.deepEqual(stuck.rows, ["- AC01 test, local: FAILED"]);
  assert.match(stuck.next!, /nobrainer-rca/);
});

test("each resume renews the contract by 30 days, capped at 90 days after creation", async () => {
  clock = T0;
  let token = (await call("start_flow_task", { outcome: "x", dod: [{ text: "pytest passes", proof: "test" }] })).json.token;
  for (const day of [25, 50, 75]) {
    clock = T0 + day * DAY;
    const b = (await resume(token)).block;
    const expires = Math.min(clock + LIFETIME_S, T0 + MAX_AGE_S);
    assert.equal(b.checkpoint, `0 of 1 accepted, contract expires ${date(expires)}`);
    assert.equal(decodeToken(b.contract, CONTRACT_PREFIX, TEST_RING, clock).expires, expires);
    token = b.contract;
  }
  assert.equal(decodeToken(token, CONTRACT_PREFIX, TEST_RING, clock).expires, T0 + MAX_AGE_S);
});

test("resume without a token is unchanged: the full card and no goal block", async () => {
  const card = getCard("event:resume")!;
  const r = await call("get_flow_step", { event: "resume" });
  assert.equal(r.isError, false);
  assert.deepEqual(r.json, { card: "event:resume", flow_version: FLOW_VERSION, rules: card.rules, source: card.source });
  assert.equal(card.rules.length, 4);
});

test("a token with any other request gets no goal block", async () => {
  clock = T0;
  const token = (await call("start_flow_task", { outcome: "x", dod: [{ text: "pytest passes", proof: "test" }] })).json.token;
  for (const args of [{ token }, { token, event: "blocked" }, { token, stage: "VERIFY" }, { token, module: "nobrainer-review" }, { token, event: "resume", module: "nobrainer-review" }]) {
    const r = await call("get_flow_step", args);
    assert.equal(r.isError, false, JSON.stringify(args));
    assert.equal(r.json.goal_block, undefined, JSON.stringify(args));
    assert.doesNotMatch(r.text, /FLOW_CONTRACT/);
  }
});

test("an invalid, expired or receipt token on resume is a recoverable error without a block", async () => {
  clock = T0;
  const forged = await call("get_flow_step", { token: "nbf1.AAAA", event: "resume" });
  assert.equal(forged.isError, true);
  assert.equal(forged.json.error.code, "TOKEN_INVALID");
  assert.ok(forged.json.error.fix);
  const token = (await call("start_flow_task", { outcome: "x", dod: [{ text: "pytest passes", proof: "test" }] })).json.token;
  const ev = await call("check_flow_evidence", { token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest", exit: 0, out: PASS }] });
  const receipt = (await call("check_flow_done", { token: ev.json.token })).json.receipt;
  const wrong = await call("get_flow_step", { token: receipt, event: "resume" });
  assert.equal(wrong.json.error.code, "TOKEN_INVALID");
  assert.match(wrong.json.error.why, /done receipt/);
  clock = T0 + LIFETIME_S + 1;
  const expired = await call("get_flow_step", { token, event: "resume" });
  assert.equal(expired.isError, true);
  assert.equal(expired.json.error.code, "TOKEN_EXPIRED");
  assert.equal(expired.json.error.fix, "call start_flow_task again with the same contract");
  for (const r of [forged, wrong, expired]) assert.doesNotMatch(r.text, /GOAL_ID|FLOW_CONTRACT/);
});

test("the goal block never repeats user-supplied text", async () => {
  clock = T0;
  const C = "CANARYr7k";
  const start = await call("start_flow_task", {
    outcome: `${C} outcome text`, non_goals: [`${C} non-goal`], local_flow: `${C}`,
    dod: [{ text: `${C} dod one`, proof: "test" }, { text: `${C} dod two`, proof: "observation" }, { text: `${C} three`, proof: "file" }],
  });
  const ev = await call("check_flow_evidence", { token: start.json.token, evidence: [
    { item: "AC01", kind: "test", cmd: `${C} cmd`, exit: 0, out: `${C}\n${PASS}` },
    { item: "AC02", kind: "observation", note: `${C} the owner confirmed the page reads well` },
    { item: "AC03", kind: "file", path: `${C}/notes.md`, sha256: "c".repeat(64) },
  ] });
  const r = await resume(ev.json.token);
  assert.ok(!r.text.toLowerCase().includes(C.toLowerCase()), r.text);
  assert.deepEqual(r.block.rows, ["- AC01 test, local: ACCEPTED", "- AC02 observation, user: ACCEPTED", "- AC03 file, static: ACCEPTED"]);
});
