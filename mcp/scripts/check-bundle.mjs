// Pre-deploy gate 2: load the built mcp.func exactly as it will be uploaded (function files plus its
// filePathMap) and answer initialize, tools/list and one tool call with a throwaway signing key.
// Usage, after `vercel build --prod`: node scripts/check-bundle.mjs [.vercel/output]
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const output = resolve(process.argv[2] ?? ".vercel/output");
const func = join(output, "functions/api/mcp.func");
const cfg = JSON.parse(readFileSync(join(func, ".vc-config.json"), "utf8"));
const dir = mkdtempSync(join(tmpdir(), "nbf-bundle-"));
let failed = false;
try {
  cpSync(func, dir, { recursive: true });
  for (const [to, from] of Object.entries(cfg.filePathMap ?? {})) {
    mkdirSync(dirname(join(dir, to)), { recursive: true });
    cpSync(resolve(output, "../..", from), join(dir, to));
  }
  process.env.VERCEL = "1";
  process.env.FLOW_TOKEN_KEYS = `1:${randomBytes(32).toString("base64")}`;
  const mod = await import(pathToFileURL(join(dir, cfg.handler)).href);
  const post = (body) => mod.POST(new Request("https://mcp.nobrainer.tech/mcp", {
    method: "POST",
    headers: { host: "mcp.nobrainer.tech", "content-type": "application/json", accept: "application/json, text/event-stream" },
    body: JSON.stringify(body),
  }));
  // Every call must be HTTP 200 with a JSON-RPC result (never an error), and each tool call must be
  // a successful tool result whose single text block parses as JSON without an error field.
  const call = async (body) => {
    const res = await post(body);
    const json = JSON.parse(await res.text());
    if (res.status !== 200 || json.error || !json.result) throw new Error(`${body.method} failed (HTTP ${res.status})`);
    return json.result;
  };
  const toolOk = (result) => {
    const text = result.content?.length === 1 && result.content[0].type === "text" ? result.content[0].text : null;
    return result.isError !== true && text !== null && !JSON.parse(text).error;
  };
  await call({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "check-bundle", version: "1" } } });
  const tools = (await call({ jsonrpc: "2.0", id: 2, method: "tools/list" })).tools ?? [];
  const advice = await call({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "recommend_flow_model", arguments: { task: "writing" } } });
  const step = await call({ jsonrpc: "2.0", id: 4, method: "tools/call", params: { name: "get_flow_step", arguments: { event: "blocked" } } });
  failed = tools.length !== 6 || !toolOk(advice) || !toolOk(step);
  console.log(`${failed ? "CHECK_BUNDLE_FAILED" : "CHECK_BUNDLE_OK"} tools=${tools.length} advisor=${toolOk(advice) ? "ok" : "error"} cards=${toolOk(step) ? "ok" : "error"}`);
} catch (err) {
  failed = true;
  console.error(`CHECK_BUNDLE_FAILED ${err.message}`);
} finally {
  rmSync(dir, { recursive: true, force: true });
}
process.exit(failed ? 1 : 0);
