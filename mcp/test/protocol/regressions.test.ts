// Regressions from the independent review of PR #88 over the wire (findings 3 and 4).
import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { startLocal, type Local } from "../helpers.ts";
import { ResourceTemplate } from "@modelcontextprotocol/server";

let local: Local;
before(async () => { local = await startLocal(); });
after(async () => { await local.close(); });

const SECRET = "gh" + "p_" + "Q7".repeat(18);
function modernHeaders(body: Record<string, any>): Record<string, string> {
  const name = body.params?.name ?? body.params?.uri;
  return { "mcp-protocol-version": "2026-07-28", "mcp-method": String(body.method), ...(typeof name === "string" && name.length < 100 ? { "mcp-name": name } : {}) };
}
const post = async (body: { method?: string } & Record<string, unknown>, modern = false) => {
  const r = await fetch(local.url, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json, text/event-stream", ...(modern ? modernHeaders(body) : {}) },
    body: JSON.stringify(body),
  });
  return { status: r.status, text: await r.text() };
};
const meta = { "io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientInfo": { name: "t", version: "1" }, "io.modelcontextprotocol/clientCapabilities": {} };
const legacyInit = { jsonrpc: "2.0", id: 0, method: "initialize", params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "t", version: "1" } } };

for (const modern of [false, true]) {
  const era = modern ? "2026-07-28" : "2025-11-25";
  const withMeta = (params: Record<string, unknown>) => (modern ? { ...params, _meta: meta } : params);

  test(`finding 3 (${era}): an unknown tool name is never logged or echoed, even when huge`, async () => {
    if (!modern) await post(legacyInit);
    for (const name of [SECRET, "x".repeat(12000)]) {
      const r = await post({ jsonrpc: "2.0", id: 1, method: "tools/call", params: withMeta({ name, arguments: {} }) }, modern);
      assert.ok(!r.text.includes(SECRET) && !r.text.includes("xxxxxxxx"), r.text.slice(0, 200));
      assert.ok(r.text.length < 400, String(r.text.length));
      assert.match(r.text, /"code":-32602/);
    }
    const logged = JSON.stringify(local.logs);
    assert.ok(!logged.includes(SECRET) && !logged.includes("xxxxxxxx"));
    assert.ok(local.logs.some((l) => l.tool === "unknown"));
  });

  test(`finding 4 (${era}): prompts/get never reflects caller text`, async () => {
    for (const args of [{ task: SECRET }, { task: "ordinary task text SENTINELp4" }, {}]) {
      const r = await post({ jsonrpc: "2.0", id: 2, method: "prompts/get", params: withMeta({ name: "flow", arguments: args }) }, modern);
      assert.ok(!r.text.includes(SECRET) && !r.text.includes("SENTINELp4"), r.text.slice(0, 300));
      assert.match(r.text, /start_flow_task/);
    }
    const unknown = await post({ jsonrpc: "2.0", id: 3, method: "prompts/get", params: withMeta({ name: SECRET }) }, modern);
    assert.ok(!unknown.text.includes(SECRET), unknown.text.slice(0, 200));
    const resource = await post({ jsonrpc: "2.0", id: 4, method: "resources/read", params: withMeta({ uri: `flow://card/${SECRET}` }) }, modern);
    assert.ok(!resource.text.includes(SECRET), resource.text.slice(0, 200));
  });

  test(`delta 4 (${era}): SDK-expanded card URIs work like literal card URIs`, async () => {
    const template = new ResourceTemplate("flow://card/{id}", { list: undefined });
    const expanded = template.uriTemplate.expand({ id: "stage:DRIFT_CHECK" });
    assert.equal(expanded, "flow://card/stage%3ADRIFT_CHECK");
    for (const uri of ["flow://card/stage:DRIFT_CHECK", expanded]) {
      const r = await post({ jsonrpc: "2.0", id: 20, method: "resources/read", params: withMeta({ uri }) }, modern);
      const reply = JSON.parse(r.text);
      assert.equal(reply.error, undefined, r.text);
      assert.match(reply.result.contents[0].text, /DRIFT_CHECK/);
    }
    for (const uri of ["flow://card/%", "flow://card/stage%3Aunknown"]) {
      const r = await post({ jsonrpc: "2.0", id: 21, method: "resources/read", params: withMeta({ uri }) }, modern);
      assert.equal(JSON.parse(r.text).error.code, -32602);
    }
  });

  test(`delta 6 (${era}): client names are screened before filtering and truncation`, async () => {
    for (const name of ["password=reviewfixture12345", "a".repeat(45) + " password=reviewfixture12345"]) {
      const before = local.logs.length;
      const body = modern
        ? { jsonrpc: "2.0", id: 22, method: "tools/list", params: { _meta: { ...meta, "io.modelcontextprotocol/clientInfo": { name, version: "1" } } } }
        : { ...legacyInit, id: 22, params: { ...legacyInit.params, clientInfo: { name, version: "1" } } };
      const r = await post(body, modern);
      assert.equal(r.status, 200, r.text);
      const logs = local.logs.slice(before);
      assert.ok(logs.some(l => l.client_name === "redacted"));
      assert.ok(!JSON.stringify(logs).includes("reviewfixture12345"));
    }
  });

  test(`delta 7 (${era}): unknown notification targets receive no JSON-RPC response`, async () => {
    for (const [method, params] of [["tools/call", { name: SECRET, arguments: {} }], ["resources/read", { uri: `flow://card/${SECRET}` }], ["prompts/get", { name: SECRET }]] as const) {
      const r = await post({ jsonrpc: "2.0", method, params: withMeta(params) }, modern);
      assert.equal(r.status, 202, r.text);
      assert.equal(r.text, "");
    }
  });
}

test("protocol errors never quote caller input (unknown method, mismatched header)", async () => {
  const unknown = await post({ jsonrpc: "2.0", id: 5, method: `x/${SECRET}` });
  assert.ok(!unknown.text.includes(SECRET), unknown.text);
  const r = await fetch(local.url, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json", "mcp-protocol-version": "2026-07-28", "mcp-method": SECRET },
    body: JSON.stringify({ jsonrpc: "2.0", id: 6, method: "tools/list", params: { _meta: meta } }),
  });
  const text = await r.text();
  assert.ok(!text.includes(SECRET), text);
  assert.match(text, /"code":-32020/);
});

test("oversized JSON-RPC ids are refused without echo", async () => {
  const r = await post({ jsonrpc: "2.0", id: "i".repeat(500), method: "ping" });
  assert.equal(r.status, 400);
  assert.ok(!r.text.includes("iiiiiiii"));
});
