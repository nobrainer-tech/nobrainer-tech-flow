// Protocol conformance with the official SDK clients against a locally running server (streamable HTTP).
import { after, before, describe, test } from "node:test";
import assert from "node:assert/strict";
import { body, connect, connectV1, startLocal, type Local } from "../helpers.ts";

const ORDER = ["start_flow_task", "get_flow_step", "check_flow_evidence", "check_flow_done", "draft_flow_handoff", "recommend_flow_model"];
const PYTEST = "tests/test_parse.py ....\n============================== 4 passed in 0.10s ==============================";
const SHA = "a".repeat(64);

let local: Local;
before(async () => { local = await startLocal(); });
after(async () => { await local.close(); });

type AnyClient = {
  listTools: () => Promise<{ tools: any[] }>;
  callTool: (p: { name: string; arguments?: Record<string, unknown> }) => Promise<unknown>;
  close: () => Promise<void>;
};

async function fullRun(c: AnyClient) {
  const start = body(await c.callTool({
    name: "start_flow_task",
    arguments: { outcome: "parse() rejects 2026-02-30", dod: [{ text: "new unit test passes", proof: "test" }, { text: "CHANGELOG.md has the entry", proof: "file" }] },
  }));
  assert.equal(start.path, "QUICK");
  assert.deepEqual(start.items.map((i: any) => i.id), ["AC01", "AC02"]);
  const ev = body(await c.callTool({
    name: "check_flow_evidence",
    arguments: { token: start.token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest -q", exit: 0, out: PYTEST, passed: 4 }] },
  }));
  assert.equal(ev.results[0].verdict, "ACCEPTED");
  assert.deepEqual(ev.open, ["AC02"]);
  const notDone = body(await c.callTool({ name: "check_flow_done", arguments: { token: ev.token } }));
  assert.equal(notDone.verdict, "NOT_DONE");
  assert.equal(notDone.receipt, undefined);
  const ev2 = body(await c.callTool({
    name: "check_flow_evidence",
    arguments: { token: ev.token, evidence: [{ item: "AC02", kind: "file", path: "CHANGELOG.md", sha256: SHA }] },
  }));
  const done = body(await c.callTool({ name: "check_flow_done", arguments: { token: ev2.token } }));
  assert.equal(done.verdict, "DONE");
  const handoff = body(await c.callTool({ name: "draft_flow_handoff", arguments: { receipt: done.receipt } }));
  assert.match(handoff.markdown, /## Proof\n- AC01 test, local, accepted/);
  return handoff;
}

for (const era of ["modern", "legacy", "v1"] as const) {
  describe(`client era ${era}`, () => {
    let c: AnyClient;
    before(async () => { c = (era === "v1" ? await connectV1(local.url) : await connect(local.url, era)) as unknown as AnyClient; });
    after(async () => { await c.close(); });

    test("lists exactly six tools in a fixed order with explicit annotations and titles", async () => {
      const { tools } = await c.listTools();
      assert.deepEqual(tools.map((t) => t.name), ORDER);
      for (const t of tools) {
        assert.ok(t.title, `${t.name} title`);
        assert.deepEqual(t.annotations, { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false });
        for (const k of ["anyOf", "oneOf", "allOf"]) assert.equal(t.inputSchema[k], undefined, `${t.name} root ${k}`);
        assert.equal(t.inputSchema.type, "object");
        assert.equal(t.inputSchema.additionalProperties, false);
        assert.equal(t.outputSchema, undefined);
        for (const p of Object.keys(t.inputSchema.properties ?? {})) assert.match(p, /^[a-z0-9_]{1,64}$/);
        assert.ok(`mcp__nobrainer-tech-flow__${t.name}`.length <= 64);
      }
    });

    test("full start -> evidence -> done -> handoff run", async () => {
      await fullRun(c);
    });

    test("resume with the contract token returns a goal block to save", async () => {
      const start = body(await c.callTool({
        name: "start_flow_task",
        arguments: { outcome: "parse() rejects 2026-02-30", dod: [{ text: "new unit test passes", proof: "test" }, { text: "CHANGELOG.md has the entry", proof: "file" }], risks: ["multi_session"] },
      }));
      const ev = body(await c.callTool({
        name: "check_flow_evidence",
        arguments: { token: start.token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest -q", exit: 0, out: PYTEST, passed: 4 }] },
      }));
      const step = body(await c.callTool({ name: "get_flow_step", arguments: { token: ev.token, event: "resume" } }));
      assert.equal(step.card, "event:resume");
      assert.equal(step.rules.length, 2);
      const lines = String(step.goal_block).split("\n");
      assert.equal(lines[0], `GOAL_ID: flow-${start.contract}`);
      assert.deepEqual(lines.filter((l) => l.startsWith("- AC")), ["- AC01 test, local: ACCEPTED", "- AC02 file, static: OPEN"]);
      assert.ok(lines.some((l) => /^CHECKPOINT: 1 of 2 accepted, contract expires \d{4}-\d{2}-\d{2}$/.test(l)));
      const saved = lines.at(-1)!.replace(/^FLOW_CONTRACT: /, "");
      assert.match(saved, /^nbf1\./);
      const notDone = body(await c.callTool({ name: "check_flow_done", arguments: { token: saved } }));
      assert.deepEqual(notDone.missing.map((m: any) => m.item), ["AC02"]);
      const plain = body(await c.callTool({ name: "get_flow_step", arguments: { event: "resume" } }));
      assert.equal(plain.goal_block, undefined);
      assert.equal(plain.rules.length, 4);
    });

    test("tool errors are isError results with code, why and fix", async () => {
      const r = (await c.callTool({ name: "check_flow_done", arguments: { token: "nbf1.AAAA" } })) as any;
      assert.equal(r.isError, true);
      assert.equal(body(r).error.code, "TOKEN_INVALID");
      assert.ok(body(r).error.fix);
    });
  });
}

test("every tool works on its own, including get_flow_step without a token", async () => {
  const c = await connect(local.url);
  const step = body(await c.callTool({ name: "get_flow_step", arguments: { event: "blocked" } }));
  assert.equal(step.card, "event:blocked");
  assert.ok(step.rules.length >= 1 && step.rules.length <= 6);
  assert.match(step.source, /^skills\/nobrainer-tech-flow\//);
  const overview = body(await c.callTool({ name: "get_flow_step", arguments: {} }));
  assert.equal(overview.card, "overview");
  const mod = body(await c.callTool({ name: "get_flow_step", arguments: { module: "nobrainer-review" } }));
  assert.ok(mod.description && mod.full);
  const advice = body(await c.callTool({ name: "recommend_flow_model", arguments: { task: "coding" } }));
  assert.equal(advice.source, "https://nobrainer.tech/ai/benchmark/");
  await c.close();
});

test("each tool's error path", async () => {
  const c = await connect(local.url);
  const cases: Array<[string, Record<string, unknown>, string]> = [
    ["start_flow_task", { outcome: "x", dod: [] }, "INVALID_INPUT"],
    ["start_flow_task", { outcome: "x", dod: [{ text: "a.md", proof: "file", level: "production" }] }, "INVALID_INPUT"],
    ["get_flow_step", { module: "nobrainer-nope" }, "UNKNOWN_CARD"],
    ["check_flow_evidence", { token: "nbf1.AAAA", evidence: [{ item: "AC01", kind: "test" }] }, "TOKEN_INVALID"],
    ["check_flow_done", { token: "garbage" }, "TOKEN_INVALID"],
    ["draft_flow_handoff", { receipt: "nbr1.AAAA" }, "TOKEN_INVALID"],
    ["recommend_flow_model", { task: "juggling" }, "INVALID_INPUT"],
    ["start_flow_task", { outcome: "x", dod: [{ text: "t", proof: "test" }], extra: 1 }, "INVALID_INPUT"],
  ];
  for (const [name, args, code] of cases) {
    const r = (await c.callTool({ name, arguments: args })) as any;
    assert.equal(r.isError, true, name);
    assert.equal(body(r).error.code, code, `${name} ${JSON.stringify(args).slice(0, 60)}`);
  }
  const start = body(await c.callTool({ name: "start_flow_task", arguments: { outcome: "x", dod: [{ text: "pytest passes", proof: "test" }] } }));
  const unknown = (await c.callTool({ name: "check_flow_evidence", arguments: { token: start.token, evidence: [{ item: "AC05", kind: "test" }] } })) as any;
  assert.equal(body(unknown).error.code, "UNKNOWN_ITEM");
  assert.equal(body(unknown).error.fix, "valid items: AC01-AC01");
  const notReceipt = (await c.callTool({ name: "draft_flow_handoff", arguments: { receipt: start.token } })) as any;
  assert.equal(body(notReceipt).error.code, "NOT_A_RECEIPT");
  await c.close();
});

test("unknown tool is a protocol error", async () => {
  const c = await connect(local.url);
  await assert.rejects(() => c.callTool({ name: "no_such_tool", arguments: {} }));
  await c.close();
});

test("prompt and resource template", async () => {
  const c = await connect(local.url);
  const p = await c.getPrompt({ name: "flow", arguments: { task: "fix the parser" } });
  assert.match(JSON.stringify(p.messages), /start_flow_task/);
  const { resources } = await c.listResources();
  assert.ok(resources.some((r) => r.uri === "flow://card/event:blocked"));
  const read = await c.readResource({ uri: "flow://card/stage:VERIFY" });
  assert.match(JSON.stringify(read.contents), /stage:VERIFY|rules/);
  await c.close();
});

describe("HTTP guards", () => {
  const post = (init: RequestInit = {}) => fetch(local.url, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json, text/event-stream", ...(init.headers as Record<string, string>) },
    body: init.body ?? JSON.stringify({ jsonrpc: "2.0", id: 1, method: "ping" }),
  });

  test("GET and DELETE return 405 with Allow: POST", async () => {
    for (const method of ["GET", "DELETE"]) {
      const r = await fetch(local.url, { method });
      assert.equal(r.status, 405);
      assert.equal(r.headers.get("allow"), "POST");
    }
  });

  test("bad Origin -> 403; allowed or missing Origin passes", async () => {
    assert.equal((await post({ headers: { origin: "https://evil.example" } })).status, 403);
    assert.notEqual((await post({ headers: { origin: "https://claude.ai" } })).status, 403);
    assert.notEqual((await post()).status, 403);
  });

  test("body over 32 KiB -> 413; wrong content type -> 415; bad JSON -> 400; never 401", async () => {
    const big = JSON.stringify({ jsonrpc: "2.0", id: 1, method: "ping", params: { pad: "x".repeat(33 * 1024) } });
    assert.equal((await post({ body: big })).status, 413);
    const r415 = await fetch(local.url, { method: "POST", headers: { "content-type": "text/plain" }, body: "{}" });
    assert.equal(r415.status, 415);
    const r400 = await post({ body: "{not json" });
    assert.equal(r400.status, 400);
    assert.equal(r400.headers.get("www-authenticate"), null);
  });

  test("hostile nesting returns a clean 400 (exactly 32 KiB of brackets; depth 9 object)", async () => {
    const brackets = "[".repeat(16384) + "]".repeat(16384);
    assert.equal(Buffer.byteLength(brackets), 32768);
    const r = await post({ body: brackets });
    assert.equal(r.status, 400);
    assert.match(await r.text(), /"code":-32600/);
    let deep: unknown = { x: 1 };
    for (let i = 0; i < 8; i++) deep = { n: deep };
    assert.equal((await post({ body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "ping", params: deep }) })).status, 400);
    assert.equal(local.logs.at(-1)?.status, 400);
  });

  test("Host allow-list rejects unknown hosts", async () => {
    const strict = await startLocal({ allowedHosts: ["mcp.nobrainer.tech"] });
    const r = await fetch(strict.url, { method: "POST", headers: { "content-type": "application/json" }, body: "{}" });
    assert.equal(r.status, 403);
    await strict.close();
  });

  test("subscriptions/listen is refused at once instead of holding an SSE stream open", async () => {
    const started = Date.now();
    const r = await post({
      headers: { "mcp-protocol-version": "2026-07-28", "mcp-method": "subscriptions/listen" },
      // The exact request shape Claude Code 2.1.303 sends right after server/discover.
      body: JSON.stringify({
        jsonrpc: "2.0", id: "listen:0", method: "subscriptions/listen",
        params: {
          _meta: { "io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientInfo": { name: "test", version: "1" }, "io.modelcontextprotocol/clientCapabilities": {} },
          notifications: { toolsListChanged: true, promptsListChanged: true, resourcesListChanged: true },
        },
      }),
    });
    const text = await r.text();
    assert.ok(Date.now() - started < 2000, "answered promptly");
    assert.match(r.headers.get("content-type") ?? "", /application\/json/);
    assert.match(text, /"error"/);
  });

  test("responses are single JSON objects, never SSE, in both eras", async () => {
    const modern = await post({ headers: { "mcp-protocol-version": "2026-07-28" } });
    const legacy = await post({ body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "x", version: "1" } } }) });
    for (const r of [modern, legacy]) assert.match(r.headers.get("content-type") ?? "", /application\/json/);
  });
});
