// Record the OpenAI review test cases with the official SDK client.
// Usage: node scripts/record-transcripts.ts [--in-memory] -> writes docs/review/test-cases.md
// Tokens are shortened in the transcript; everything else is the server's exact output.
import { writeFileSync } from "node:fs";
import { Client, InMemoryTransport, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";
import { startServer } from "./serve.ts";
import { createHttpHandler } from "../src/http.ts";
import { optionsFromEnv } from "../src/config.ts";
import { buildServer, SERVER_VERSION } from "../src/server.ts";

const inMemory = process.argv.includes("--in-memory");
const options = optionsFromEnv({});
const client = new Client({ name: "review-recorder", version: "1.0.0" }, { versionNegotiation: { mode: inMemory ? "legacy" : { pin: "2026-07-28" } } } as never);
let closeServer: () => Promise<void>;
if (inMemory) {
  const server = buildServer({ ring: options.ring, limiter: options.limiter, now: () => Math.floor(Date.now() / 1000) });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await server.connect(serverTransport);
  closeServer = () => server.close();
  await client.connect(clientTransport);
} else {
  const server = await startServer(createHttpHandler({ ...options, log: () => {} }), 0);
  const address = server.address();
  const url = new URL(`http://127.0.0.1:${typeof address === "object" && address ? address.port : 0}/mcp`);
  closeServer = () => new Promise((resolve) => server.close(() => resolve()));
  await client.connect(new StreamableHTTPClientTransport(url));
}
const protocolVersion = client.getNegotiatedProtocolVersion();

const short = (s: string) => s.replace(/(nb[fr]1\.)[A-Za-z0-9_-]{12,}/g, (_, p: string) => `${p}<token>`);
const lines: string[] = [];
const checks: string[] = [];
async function call(name: string, args: Record<string, unknown>) {
  const r = (await client.callTool({ name, arguments: args })) as { content: Array<{ text: string }>; isError?: boolean };
  const text = r.content[0]!.text;
  lines.push(`Call \`${name}\`${r.isError ? " (isError)" : ""}`, "", "```json", short(JSON.stringify(args, null, 1)), "```", "", "Result", "", "```json", short(JSON.stringify(JSON.parse(text), null, 1)), "```", "");
  return JSON.parse(text);
}
function expect(label: string, ok: boolean) {
  checks.push(`- ${ok ? "PASS" : "FAIL"} ${label}`);
  lines.push(`Check: ${ok ? "PASS" : "FAIL"} - ${label}`, "");
}
function header(id: string, title: string, prompt: string, tools: string, expected: string) {
  lines.push(`## ${id}. ${title}`, "", `Prompt: "${prompt}"`, "", `Expected tools: ${tools}`, "", `Expected result: ${expected}`, "");
}

const FAIL_OUT = "FAILED tests/test_dates.py::test_feb_30 - DID NOT RAISE ValueError\n========================= 1 failed, 4 passed in 0.21s =========================";
const PASS_OUT = "tests/test_dates.py .....\n============================== 5 passed in 0.18s ===============================";

header("P1", "Start a contract", "Use NoBrainer Tech Flow. I need the date parser bug fixed: parse('2026-02-30') should raise an error. Done means the new unit test passes and the change is documented in CHANGELOG.md.", "start_flow_task", "Path QUICK, items AC01 (test, local) and AC02 (file, static), first step DRIFT_CHECK, a token");
const p1 = await call("start_flow_task", { outcome: "parse('2026-02-30') raises an error for library users", dod: [{ text: "new unit test for 2026-02-30 passes", proof: "test" }, { text: "CHANGELOG.md documents the fix", proof: "file" }] });
expect("QUICK path with AC01 test/local and AC02 file/static and a DRIFT_CHECK step", p1.path === "QUICK" && p1.items[0].level === "local" && p1.items[1].level === "static" && p1.next.stage === "DRIFT_CHECK");

header("P2", "Guidance for a blocker", "With NoBrainer Tech Flow: I can't run the tests because the CI runner is down. What should I do?", "get_flow_step (event blocked)", "Up to six rules from the Flow delivery reference: identify the failed operation, try a permitted alternative, never evade a denial, continue independent items, and the four blocker categories");
const p2 = await call("get_flow_step", { event: "blocked" });
expect("blocked card with 1-6 verbatim rules and a source", p2.card === "event:blocked" && p2.rules.length >= 1 && p2.rules.length <= 6 && /delivery\.md|SKILL\.md/.test(p2.source));

header("P3", "Evidence: a failing run and an inconsistent claim", "Here is the pytest output (it ends with 1 failed, 4 passed). The tests pass, right?", "check_flow_evidence", "AC01 FAILED; a record claiming failed: 0 for the same output is REJECTED with COUNTS_MISMATCH");
const p3 = await call("check_flow_evidence", { token: p1.token, evidence: [
  { item: "AC01", kind: "test", cmd: "pytest -q", exit: 1, out: FAIL_OUT },
  { item: "AC01", kind: "test", cmd: "pytest -q", exit: 1, out: FAIL_OUT, failed: 0 },
] });
expect("FAILED then REJECTED COUNTS_MISMATCH", p3.results[0].verdict === "FAILED" && p3.results[1].code === "COUNTS_MISMATCH");

header("P4", "Done gate and a gap-aware handoff", "I fixed it and the tests pass now. Is the task done? I have no access to the changelog, so mark AC02 as not checked and write the handoff.", "check_flow_evidence, check_flow_done, draft_flow_handoff", "NOT_DONE with AC02 missing; then DONE_WITH_GAPS and a handoff that lists AC01 proof and AC02 under Not checked");
const p4a = await call("check_flow_evidence", { token: p3.token, evidence: [{ item: "AC01", kind: "test", cmd: "pytest -q", exit: 0, out: PASS_OUT, passed: 5, failed: 0 }] });
const p4b = await call("check_flow_done", { token: p4a.token });
expect("NOT_DONE with AC02 missing and no receipt", p4b.verdict === "NOT_DONE" && p4b.missing[0]?.item === "AC02" && !p4b.receipt);
const p4c = await call("check_flow_done", { token: p4a.token, unchecked: [{ item: "AC02", reason: "no access to the repository changelog" }] });
const p4d = await call("draft_flow_handoff", { receipt: p4c.receipt });
expect("DONE_WITH_GAPS and the handoff lists AC01 proof and AC02 not checked", p4c.verdict === "DONE_WITH_GAPS" && /AC01 test, local, accepted/.test(p4d.markdown) && /## Not checked\n- AC02/.test(p4d.markdown));

header("P5", "Model advice from the benchmark", "With NoBrainer Tech Flow: I use Codex and Claude Code. Recommend a model using the legacy task Coding.", "recommend_flow_model", "The case-insensitive legacy Coding alias returns task terminal-coding with a nonempty top-3 shortlist, quality, cost and time from the pinned benchmark snapshot, its date, expiry and the source URL");
const p5 = await call("recommend_flow_model", { task: "Coding", have: ["codex", "claude-code"] });
expect("legacy Coding maps to terminal-coding with a nonempty shortlist", p5.task === "terminal-coding" && Array.isArray(p5.shortlist) && p5.shortlist.length >= 1);
expect("shortlist of 1-3 with snapshot date and source", Array.isArray(p5.shortlist) && p5.shortlist.length >= 1 && p5.shortlist.length <= 3 && typeof p5.snapshot === "string" && p5.source === "https://nobrainer.tech/ai/benchmark/");

await client.close();
await closeServer();

const negative = [
  "## Negative cases (the model should not call Flow tools)",
  "",
  "These are model behaviours, so they are checked in the client, not by the server. Every tool is read-only",
  "(`readOnlyHint: true`, `openWorldHint: false`), so no tool can deploy or change anything even if called.",
  "",
  "| # | Prompt | Why the plugin should not act | Expected behaviour |",
  "|---|---|---|---|",
  "| N1 | \"What is the capital of Australia?\" | A simple fact; no task contract is needed | Direct answer, no Flow tool call |",
  "| N2 | \"Write a four-line poem about autumn.\" | Creative chat with no proof to check | Direct answer, no Flow tool call |",
  "| N3 | \"Deploy my app to production now.\" | The plugin does not deploy or run commands | No Flow tool call that claims an effect; the model says the plugin does not deploy |",
  "",
];
const doc = [
  "# OpenAI review test cases",
  "",
  `Recorded with \`npm run transcripts${inMemory ? " -- --in-memory" : ""}\` (${SERVER_VERSION}, MCP ${protocolVersion}, official`,
  `TypeScript SDK client; ${inMemory ? "InMemoryTransport with buildServer, no HTTP listener" : "Streamable HTTP against a local server"}).`,
  "Tokens are shortened to `<token>`; all other output is exact. The five positive",
  "cases cover all six tools. Paste the prompts and expected results into the portal review form.",
  "",
  "## Summary",
  "",
  ...checks,
  "",
  ...lines,
  ...negative,
].join("\n");
writeFileSync(new URL("../docs/review/test-cases.md", import.meta.url), `${doc}\n`);
console.log(checks.join("\n"));
if (checks.some((c) => c.startsWith("- FAIL "))) process.exit(1);
