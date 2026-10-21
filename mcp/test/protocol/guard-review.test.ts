// Review findings 4, 6 and 7 through the HTTP handler and SDK without binding a socket.
import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import { ResourceTemplate } from "@modelcontextprotocol/server";
import { createHttpHandler } from "../../src/http.ts";
import { cardIds } from "../../src/content/cards.ts";
import { findSecret } from "../../src/evidence/secrets.ts";
import { memoryLimiter } from "../../src/ratelimit.ts";
import { parseKeyRing } from "../../src/token.ts";
import type { LogLine } from "../../src/log.ts";

const SECRET = "gh" + "p_" + "Q7".repeat(18);
const ring = parseKeyRing(`7:${randomBytes(32).toString("base64")}`);
const bounded = { timeout: 10000 };

function harness(modern = false) {
  const logs: LogLine[] = [];
  const handle = createHttpHandler({
    ring, limiter: memoryLimiter(), allowedOrigins: [], allowedHosts: "loopback",
    log: line => logs.push(line),
  });
  const era = modern ? "2026-07-28" : "2025-11-25";
  const meta = {
    "io.modelcontextprotocol/protocolVersion": era,
    "io.modelcontextprotocol/clientInfo": { name: "guard-review", version: "1" },
    "io.modelcontextprotocol/clientCapabilities": {},
  };
  const post = async (method: string, params: Record<string, any>, notification = false, origin?: string) => {
    const target = params.name ?? params.uri;
    const headers = {
      "content-type": "application/json", accept: "application/json, text/event-stream",
      ...(modern ? { "mcp-protocol-version": era, "mcp-method": method, ...(typeof target === "string" ? { "mcp-name": target } : {}) } : {}),
      ...(origin === undefined ? {} : { origin }),
    };
    const response = await handle(new Request("http://127.0.0.1/mcp", {
      method: "POST", headers, signal: AbortSignal.timeout(5000),
      body: JSON.stringify({
        jsonrpc: "2.0", ...(notification ? {} : { id: 1 }), method,
        params: modern ? { ...params, _meta: { ...meta, ...params._meta } } : params,
      }),
    }));
    return { status: response.status, text: await response.text() };
  };
  return { post, logs, era };
}

for (const modern of [false, true]) {
  const era = modern ? "2026-07-28" : "2025-11-25";

  test(`guard review 4 (${era}): every SDK-expanded card has its decoded identity`, bounded, async () => {
    const { post } = harness(modern);
    const template = new ResourceTemplate("flow://card/{id}", { list: undefined });
    assert.equal(template.uriTemplate.expand({ id: "stage:DRIFT_CHECK" }), "flow://card/stage%3ADRIFT_CHECK");
    for (const id of cardIds()) {
      const response = await post("resources/read", { uri: template.uriTemplate.expand({ id }) });
      const reply = JSON.parse(response.text);
      assert.equal(response.status, 200);
      assert.equal(reply.error, undefined, "known card rejected");
      assert.equal(JSON.parse(reply.result.contents[0].text).id, id);
    }
    for (const uri of ["flow://card/%", "flow://card/stage%3Aunknown", "flow://card/stage%253ADRIFT_CHECK"]) {
      const response = await post("resources/read", { uri });
      assert.equal(JSON.parse(response.text).error.code, -32602);
      assert.ok(response.text.length < 400);
    }
  });

  test(`guard review 6 (${era}): raw client secrets are redacted before lossy transforms`, bounded, async () => {
    const { post, logs } = harness(modern);
    for (const name of ["password=guardfixture12345", "z".repeat(45) + " password=guardfixture12345", SECRET, "sk-" + "proj-" + "q7".repeat(30)]) {
      assert.ok(findSecret(name), "fixture must trigger scanner");
      const before = logs.length;
      const response = modern
        ? await post("tools/list", { _meta: { "io.modelcontextprotocol/clientInfo": { name, version: "1" } } })
        : await post("initialize", { protocolVersion: era, capabilities: {}, clientInfo: { name, version: "1" } });
      assert.equal(response.status, 200);
      assert.equal(logs.length, before + 1);
      assert.ok(logs[before]?.client_name === "redacted", "raw client input was not redacted");
      const logged = JSON.stringify(logs[before]);
      assert.equal(findSecret(logged), null, "detected input reached log");
      assert.ok(!logged.includes("guardfixture12345") && !logged.includes(SECRET), "fixture value reached log");
    }
  });

  test(`guard review 7 (${era}): id-less notifications return 202 with an empty body`, bounded, async () => {
    const { post } = harness(modern);
    for (const [method, params] of [
      ["tools/call", { name: SECRET, arguments: {} }],
      ["resources/read", { uri: `flow://card/${SECRET}` }],
      ["prompts/get", { name: SECRET }],
      ["notifications/initialized", {}], ["ping", {}],
    ] as const) {
      const response = await post(method, params, true);
      assert.equal(response.status, 202);
      assert.equal(response.text, "");
    }
  });
}

test("guard review 6: rejected origins are screened before host extraction, filtering and truncation", bounded, async () => {
  const { post, logs } = harness();
  for (const origin of [
    "https://password=guardfixture12345",
    `https://${SECRET}`,
    "https://" + "z".repeat(85) + ":password=guardfixture12345",
    "https://denied.example/password=guardfixture12345",
  ]) {
    assert.ok(findSecret(origin), "fixture must trigger scanner");
    const response = await post("ping", {}, false, origin);
    assert.equal(response.status, 403);
    assert.equal(response.text, "Forbidden origin");
    assert.ok(logs.at(-1)?.rejected_origin === "redacted", "raw origin input was not redacted");
    const logged = JSON.stringify(logs.at(-1));
    assert.equal(findSecret(logged), null, "detected input reached log");
    assert.ok(!logged.includes("guardfixture12345") && !logged.includes(SECRET), "fixture value reached log");
  }
  for (const [origin, expected] of [
    ["https://denied.example/path", "denied.example"],
    ["https://" + "z".repeat(100), "z".repeat(80)],
  ]) {
    const response = await post("ping", {}, false, origin);
    assert.equal(response.status, 403);
    assert.equal(logs.at(-1)?.rejected_origin, expected);
  }
});
