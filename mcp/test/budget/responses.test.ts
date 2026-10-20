// Response budgets (spec 10.3): golden fixtures <= 400 tokens; fuzzed worst cases <= 600 tokens and 1,500 bytes.
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import { findSecret } from "../../src/evidence/secrets.ts";
import { tokens, TEST_RING } from "../helpers.ts";
import { runTool } from "../../src/server.ts";
import { TOOLS } from "../../src/tools/index.ts";
import { memoryLimiter } from "../../src/ratelimit.ts";
import { MODULES, cardIds, getCard } from "../../src/content/cards.ts";
import { PROOFS, REACHABLE, RISKS } from "../../src/rules/levels.ts";
import type { ToolContext } from "../../src/tools/common.ts";

const ctx: ToolContext = { ring: TEST_RING, now: () => Math.floor(Date.now() / 1000), limiter: memoryLimiter(1e9) };
const tool = (name: string) => TOOLS.find((t) => t.name === name)!;
async function run(name: string, args: unknown) {
  const r = await runTool(tool(name), args, ctx);
  const text = r.content[0]!.text;
  return { text, json: JSON.parse(text), isError: r.isError === true };
}
const check = (label: string, text: string, cap: number) => {
  const n = tokens(text);
  assert.ok(n <= cap, `${label}: ${n} tokens`);
  assert.ok(Buffer.byteLength(text) <= 1500, `${label}: ${Buffer.byteLength(text)} bytes`);
  assert.match(text, /^[\x20-\x7e]*$/, `${label}: ASCII`);
  return n;
};

const PASS = "============================== 4 passed in 0.10s ==============================";
const sizes: Record<string, number> = {};

test("golden fixtures per tool are <= 400 tokens", async () => {
  const start = await run("start_flow_task", { outcome: "Date parser rejects 2026-02-30", dod: [
    { text: "new unit test passes", proof: "test" }, { text: "docs at https://example.com/parser", proof: "url" }, { text: "CHANGELOG.md entry", proof: "file" },
  ], risks: ["external_effect"] });
  sizes.start = check("start", start.text, 400);
  const ev = await run("check_flow_evidence", { token: start.json.token, evidence: [
    { item: "AC01", kind: "test", cmd: "pytest", exit: 0, out: PASS }, { item: "AC02", kind: "url", url: "http://localhost:3000/parser", status: 200 },
  ] });
  sizes.evidence = check("evidence", ev.text, 400);
  const done = await run("check_flow_done", { token: ev.json.token, unchecked: [{ item: "AC03", reason: "no repo access" }] });
  sizes.done = check("done", done.text, 400);
  const done2 = await run("check_flow_done", { token: ev.json.token, unchecked: [{ item: "AC02", reason: "no deploy yet" }, { item: "AC03", reason: "no repo access" }] });
  const handoff = await run("draft_flow_handoff", { receipt: done2.json.receipt });
  sizes.handoff = check("handoff", handoff.text, 400);
  sizes.step = check("step", (await run("get_flow_step", { event: "blocked" })).text, 400);
  sizes.advisor = check("advisor", (await run("recommend_flow_model", { task: "terminal-coding", have: ["codex", "anthropic"] })).text, 400);
  const err = await run("check_flow_done", { token: "nbf1.AAAA" });
  sizes.error = check("error", err.text, 120);
  console.log(`RESPONSE_TOKENS ${JSON.stringify(sizes)}`);
});

test("every card response and UNKNOWN_CARD error fit the budget", async () => {
  for (const id of cardIds()) {
    const [kind, name] = id.includes(":") ? id.split(":") : ["overview", ""];
    const args = kind === "stage" ? { stage: name } : kind === "event" ? { event: name } : kind === "module" ? { module: name } : {};
    if (kind !== "stage" && kind !== "event" && kind !== "module" && id !== "overview") continue;
    const r = await run("get_flow_step", args);
    assert.equal(r.isError, false, id);
    check(id, r.text, 600);
    assert.ok(tokens(JSON.stringify(getCard(id))) <= 350, `card ${id}`);
  }
  check("unknown card", (await run("get_flow_step", { module: "nobrainer-zzz" })).text, 150);
  assert.ok(MODULES.length >= 18);
});

// Valid free text: at least one visible character and nothing secret-shaped.
const text = (max: number) =>
  fc.string({ minLength: 1, maxLength: max, unit: "grapheme-ascii" }).filter((s) => s.trim().length > 0 && findSecret(s) === null);
const startArgs = fc.record({
  outcome: text(300),
  // Only valid proof/level pairs, so every generated contract must succeed (finding 12).
  dod: fc.array(fc.constantFrom(...PROOFS).chain((proof) => fc.record({ text: text(160), proof: fc.constant(proof), level: fc.constantFrom(...REACHABLE[proof]) })), { minLength: 10, maxLength: 10 }),
  non_goals: fc.array(text(120), { maxLength: 5 }),
  risks: fc.uniqueArray(fc.constantFrom(...RISKS), { maxLength: 6 }),
  local_flow: fc.constantFrom("1.0.0", "x", "9.9.9"),
});

test("fuzz: start_flow_task at maximum sizes stays within 600 tokens and 1,500 bytes", async () => {
  await fc.assert(fc.asyncProperty(startArgs, async (args) => {
    const r = await run("start_flow_task", args);
    check("fuzz start", r.text, 600);
    assert.equal(r.isError, false, r.text.slice(0, 160));
    assert.match(r.json.token, /^nbf1\./);
  }), { numRuns: 150 });
});

test("fuzz: evidence with 4 maximal records and done with 10 unchecked items stay within budget", async () => {
  const dod = Array.from({ length: 10 }, (_, i) => ({ text: `item ${i} check passes`, proof: "test" }));
  const s = await run("start_flow_task", { outcome: "x", dod, risks: ["irreversible"] });
  const rec = fc.record({
    item: fc.constantFrom(...Array.from({ length: 10 }, (_, i) => `AC${String(i + 1).padStart(2, "0")}`)),
    kind: fc.constantFrom(...PROOFS),
    cmd: text(300), exit: fc.integer({ min: -1, max: 2 }), out: fc.oneof(text(4000), fc.constant(PASS)),
    passed: fc.nat(9), failed: fc.nat(3), path: text(300), sha256: fc.constant("b".repeat(64)),
    url: fc.constantFrom("https://example.com/a", "http://localhost/x", "notaurl"), status: fc.integer({ min: 100, max: 599 }), note: text(300),
  });
  await fc.assert(fc.asyncProperty(fc.array(rec, { minLength: 4, maxLength: 4 }), async (evidence) => {
    const r = await run("check_flow_evidence", { token: s.json.token, evidence });
    check("fuzz evidence", r.text, 600);
    assert.ok(!["BUDGET_EXCEEDED", "INTERNAL"].includes(r.json.error?.code), r.text.slice(0, 160));
    if (!r.isError) {
      const unchecked = Array.from({ length: 10 }, (_, i) => ({ item: `AC${String(i + 1).padStart(2, "0")}`, reason: "x".repeat(200) }));
      check("fuzz done", (await run("check_flow_done", { token: r.json.token })).text, 600);
      const d = await run("check_flow_done", { token: r.json.token, unchecked });
      check("fuzz done gaps", d.text, 600);
      if (d.json.receipt) check("fuzz handoff", (await run("draft_flow_handoff", { receipt: d.json.receipt })).text, 600);
    }
  }), { numRuns: 120 });
});

test("contract token stays <= 180 tokens at maximum size", async () => {
  const dod = Array.from({ length: 10 }, (_, i) => ({ text: `item ${i}`, proof: "file" as const }));
  let t = (await run("start_flow_task", { outcome: "x", dod })).json.token as string;
  for (let i = 0; i < 3; i++) {
    const evidence = Array.from({ length: 4 }, (_, k) => ({ item: `AC0${k + 1}`, kind: "file", path: `f${i}${k}.txt`, sha256: String(i).repeat(64) }));
    t = (await run("check_flow_evidence", { token: t, evidence })).json.token;
  }
  const n = tokens(t);
  console.log(`TOKEN_TOKENS ${n} chars=${t.length}`);
  assert.ok(n <= 180, String(n));
});
