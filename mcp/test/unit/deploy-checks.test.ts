// Findings 9 and 10: the pre-deploy gates must fail on mapped native files and on JSON-RPC errors.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const script = (name: string) => fileURLToPath(new URL(`../../scripts/${name}`, import.meta.url));

function fakeOutput(t: { after: (fn: () => void) => void }, mapped: Record<string, string>, handler = "") {
  const root = mkdtempSync(join(tmpdir(), "nbf-out-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const out = join(root, ".vercel/output");
  for (const fn of ["mcp", "spend-hook", "challenge"]) {
    const dir = join(out, `functions/api/${fn}.func`);
    mkdirSync(join(dir, "api"), { recursive: true });
    const cfg = { handler: `api/${fn}.js`, runtime: "nodejs22.x", architecture: "x86_64", filePathMap: fn === "mcp" ? mapped : {} };
    writeFileSync(join(dir, ".vc-config.json"), JSON.stringify(cfg));
    writeFileSync(join(dir, `api/${fn}.js`), handler || "export const POST = () => new Response('{}');");
  }
  writeFileSync(join(out, "config.json"), "{\"version\":3}");
  for (const src of Object.values(mapped)) {
    mkdirSync(join(root, src, ".."), { recursive: true });
    writeFileSync(join(root, src), "x");
  }
  return out;
}

function run(name: string, out: string): { code: number; text: string } {
  try {
    return { code: 0, text: execFileSync(process.execPath, [script(name), out], { encoding: "utf8", stdio: "pipe" }) };
  } catch (err) {
    const e = err as { status: number; stdout: string; stderr: string };
    return { code: e.status, text: `${e.stdout}${e.stderr}` };
  }
}

test("finding 9: check-output fails on a native or darwin file reached through filePathMap", (t) => {
  assert.equal(run("check-output.mjs", fakeOutput(t, { "dist/a.js": "dist/a.js" })).code, 0);
  const bad = run("check-output.mjs", fakeOutput(t, { "node_modules/x/native-darwin-arm64/addon.node": "node_modules/x/native-darwin-arm64/addon.node" }));
  assert.equal(bad.code, 1);
  assert.match(bad.text, /native module|darwin/);
});

test("finding 10: check-bundle fails when a tool call returns a JSON-RPC error", (t) => {
  const handler = `
    export async function POST(req) {
      const m = await req.json();
      const body = m.method === "initialize" ? { jsonrpc: "2.0", id: m.id, result: { protocolVersion: "2025-11-25" } }
        : m.method === "tools/list" ? { jsonrpc: "2.0", id: m.id, result: { tools: [1, 2, 3, 4, 5, 6] } }
        : { jsonrpc: "2.0", id: m.id, error: { code: -32603, message: "boom" } };
      return new Response(JSON.stringify(body), { status: 200 });
    }`;
  const r = run("check-bundle.mjs", fakeOutput(t, {}, handler));
  assert.equal(r.code, 1, r.text);
  assert.match(r.text, /CHECK_BUNDLE_FAILED/);
});
