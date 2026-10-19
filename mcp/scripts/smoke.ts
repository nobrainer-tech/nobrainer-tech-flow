// Live readback after a deploy: node scripts/smoke.ts https://mcp.nobrainer.tech/mcp [--challenge <token>]
// Lists tools in both protocol eras, runs start -> evidence -> done -> handoff and the advisor, checks
// the guards (GET 405, bad Origin 403) and, with --challenge, the OpenAI domain-verification file.
import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";

const url = new URL(process.argv[2] ?? "http://127.0.0.1:8787/mcp");
const ci = process.argv.indexOf("--challenge");
const challenge = ci > 0 ? process.argv[ci + 1] : undefined;
const EXPECTED = ["start_flow_task", "get_flow_step", "check_flow_evidence", "check_flow_done", "draft_flow_handoff", "recommend_flow_model"];
const failures: string[] = [];
const ok = (cond: unknown, label: string) => {
  console.log(`${cond ? "PASS" : "FAIL"} ${label}`);
  if (!cond) failures.push(label);
};
const text = (r: unknown) => JSON.parse((r as { content: Array<{ text: string }> }).content[0]!.text);

for (const era of ["modern", "legacy"] as const) {
  const client = new Client({ name: "nbf-smoke", version: "1.0.0" }, { versionNegotiation: { mode: era === "modern" ? { pin: "2026-07-28" } : "legacy" } } as never);
  await client.connect(new StreamableHTTPClientTransport(url));
  const { tools } = await client.listTools();
  ok(JSON.stringify(tools.map((t) => t.name)) === JSON.stringify(EXPECTED), `${era}: tools/list returns the six tools (${client.getNegotiatedProtocolVersion()}, ${client.getServerVersion()?.version})`);
  const start = text(await client.callTool({ name: "start_flow_task", arguments: { outcome: "smoke test", dod: [{ text: "smoke test passes", proof: "test" }] } }));
  const pass = "============================== 1 passed in 0.01s ==============================";
  const ev = text(await client.callTool({ name: "check_flow_evidence", arguments: { token: start.token, evidence: [{ item: "AC01", kind: "test", cmd: "smoke", exit: 0, out: pass }] } }));
  const done = text(await client.callTool({ name: "check_flow_done", arguments: { token: ev.token } }));
  const handoff = text(await client.callTool({ name: "draft_flow_handoff", arguments: { receipt: done.receipt } }));
  ok(ev.results?.[0]?.verdict === "ACCEPTED" && done.verdict === "DONE" && /## Proof/.test(handoff.markdown ?? ""), `${era}: full run ends DONE with a handoff`);
  const advice = text(await client.callTool({ name: "recommend_flow_model", arguments: { task: "coding" } }));
  ok(advice.source === "https://nobrainer.tech/ai/benchmark/" && typeof advice.snapshot === "string", `${era}: advisor reports snapshot ${advice.snapshot}`);
  await client.close();
}

ok((await fetch(url)).status === 405, "GET returns 405");
const bad = await fetch(url, { method: "POST", headers: { origin: "https://evil.example", "content-type": "application/json" }, body: "{}" });
ok(bad.status === 403, "foreign Origin returns 403");
if (challenge) {
  const res = await fetch(new URL("/.well-known/openai-apps-challenge", url));
  ok(res.status === 200 && (await res.text()).trim() === challenge, "OpenAI challenge file returns the exact token");
}
if (failures.length) {
  console.error(`SMOKE_FAILED ${failures.length}`);
  process.exit(1);
}
console.log(`SMOKE_OK ${url.href}`);
