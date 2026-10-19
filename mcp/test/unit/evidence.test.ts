import { test } from "node:test";
import assert from "node:assert/strict";
import { applyEvidence, isCurrent, isStale, type EvidenceRecord } from "../../src/evidence/checks.ts";
import { isPublicHost, levelSatisfies, kindMatches, type Level, type Proof } from "../../src/rules/levels.ts";
import type { TokenState } from "../../src/token.ts";

function state(items: Array<[Proof, Level]>): TokenState {
  return {
    kid: 0, full: false, verdict: "NONE", risks: [], contract: Buffer.alloc(8), created: 0, expires: 1, flow: [2, 4, 1], epoch: 0,
    items: items.map(([proof, level]) => ({ proof, level, failures: 0, status: "OPEN", kind: null, unchecked: false, epoch: 0, digest: Buffer.alloc(4) })),
    files: [],
  };
}

const PYTEST_PASS = "collected 5 items\n\ntests/test_x.py .....\n\n============================== 5 passed in 0.12s ===============================";
const PYTEST_FAIL = "FAILED tests/test_x.py::test_parse\n========================= 1 failed, 4 passed in 0.31s =========================";
const run = (out: string, exit: number, extra: Partial<EvidenceRecord> = {}): EvidenceRecord => ({ item: "AC01", kind: "test", cmd: "pytest -q", exit, out, ...extra });
const sha = (c: string) => c.repeat(64);

test("passing test accepted at local; claimed counts must match", () => {
  const s = state([["test", "local"]]);
  const r = applyEvidence(s, [run(PYTEST_PASS, 0, { passed: 5, failed: 0 })]).results[0];
  assert.equal(r?.verdict, "ACCEPTED");
  assert.equal(r?.level, "local");
  assert.match(r?.digest ?? "", /^[0-9a-f]{8}$/);
});

test("P3: failing run is FAILED; a false claim on the same output is COUNTS_MISMATCH", () => {
  const s = state([["test", "local"]]);
  const out = applyEvidence(s, [run(PYTEST_FAIL, 1), run(PYTEST_FAIL, 1, { failed: 0 })]);
  assert.equal(out.results[0]?.verdict, "FAILED");
  assert.equal(out.results[1]?.verdict, "REJECTED");
  assert.equal(out.results[1]?.code, "COUNTS_MISMATCH");
});

test("exit 0 with failing summary is EXIT_OUTPUT_CONFLICT; no summary is NO_TEST_SUMMARY", () => {
  const s = state([["test", "local"]]);
  const [a, b] = applyEvidence(s, [run(PYTEST_FAIL, 0), run("all good", 0)]).results;
  assert.equal(a?.code, "EXIT_OUTPUT_CONFLICT");
  assert.equal(b?.code, "NO_TEST_SUMMARY");
});

test("command item accepts test evidence; failing summary under exit 0 is rejected", () => {
  const s = state([["command", "local"]]);
  assert.equal(applyEvidence(s, [run(PYTEST_PASS, 0)]).results[0]?.verdict, "ACCEPTED");
  const c = applyEvidence(s, [{ item: "AC01", kind: "command", cmd: "make check", exit: 0, out: PYTEST_FAIL }]).results[0];
  assert.equal(c?.code, "EXIT_OUTPUT_CONFLICT");
});

test("level ladder: localhost URL proves local only; public https proves production", () => {
  const s = state([["url", "deployed"], ["url", "local"], ["url", "delivered"]]);
  const res = applyEvidence(s, [
    { item: "AC01", kind: "url", url: "http://localhost:3000/", status: 200 },
    { item: "AC02", kind: "url", url: "http://127.0.0.1:8080/x", status: 200 },
    { item: "AC03", kind: "url", url: "https://example.com/post/1", status: 200 },
  ]).results;
  assert.equal(res[0]?.code, "LEVEL_TOO_LOW");
  assert.equal(res[1]?.verdict, "ACCEPTED");
  assert.equal(res[2]?.level, "production");
});

test("url status outside 200-399 fails; public http is NOT_HTTPS", () => {
  const s = state([["url", "deployed"]]);
  const res = applyEvidence(s, [
    { item: "AC01", kind: "url", url: "https://example.com/", status: 500 },
    { item: "AC01", kind: "url", url: "http://example.com/", status: 200 },
  ]).results;
  assert.equal(res[0]?.verdict, "FAILED");
  assert.equal(res[1]?.code, "NOT_HTTPS");
});

test("a test with a public https url proves deployed", () => {
  const s = state([["test", "deployed"]]);
  const r = applyEvidence(s, [run(PYTEST_PASS, 0, { url: "https://staging.example.com" })]).results[0];
  assert.equal(r?.level, "deployed");
});

test("kind matching", () => {
  const s = state([["file", "static"]]);
  assert.equal(applyEvidence(s, [run(PYTEST_PASS, 0)]).results[0]?.code, "KIND_MISMATCH");
  assert.ok(kindMatches("test", "command"));
  assert.ok(!kindMatches("command", "test"));
});

test("staleness: a new hash for a registered file stales earlier test acceptances", () => {
  const s = state([["test", "local"], ["file", "static"]]);
  applyEvidence(s, [run(PYTEST_PASS, 0), { item: "AC02", kind: "file", path: "./src/a.ts", sha256: sha("a") }]);
  assert.ok(isCurrent(s.items[0]!, s.epoch));
  applyEvidence(s, [{ item: "AC02", kind: "file", path: "src/a.ts", sha256: sha("b") }]);
  assert.equal(s.epoch, 1);
  assert.ok(isStale(s.items[0]!, s.epoch));
  assert.ok(isCurrent(s.items[1]!, s.epoch), "file evidence itself is current");
  applyEvidence(s, [run(PYTEST_PASS, 0)]);
  assert.ok(isCurrent(s.items[0]!, s.epoch), "a re-run after the change is current");
});

test("same hash again does not stale; registry evicts the oldest beyond 8 files", () => {
  const s = state([["file", "static"]]);
  for (let i = 0; i < 10; i++) applyEvidence(s, [{ item: "AC01", kind: "file", path: `f${i}.txt`, sha256: sha("c") }]);
  assert.equal(s.files.length, 8);
  assert.equal(s.epoch, 0);
});

test("bad path and missing fields are rejected", () => {
  const s = state([["file", "static"], ["observation", "user"]]);
  const res = applyEvidence(s, [
    { item: "AC01", kind: "file", path: "../etc/x", sha256: sha("d") },
    { item: "AC01", kind: "file", path: "a.txt" },
    { item: "AC02", kind: "observation", note: "short" },
  ]).results;
  assert.deepEqual(res.map((r) => r.code), ["BAD_PATH", "MISSING_FIELD", "NOTE_TOO_SHORT"]);
});

test("failure budget: the second FAILED record returns REPEATED_DEFECT", () => {
  const s = state([["test", "local"]]);
  assert.equal(applyEvidence(s, [run(PYTEST_FAIL, 1)]).repeated, false);
  const out = applyEvidence(s, [run(PYTEST_FAIL, 1)]);
  assert.equal(out.repeated, true);
  assert.equal(out.results[0]?.code, "REPEATED_DEFECT");
});

test("one output proving two items is accepted with a SAME_OUTPUT warning", () => {
  const s = state([["test", "local"], ["test", "local"]]);
  const out = applyEvidence(s, [run(PYTEST_PASS, 0), { ...run(PYTEST_PASS, 0), item: "AC02" }]);
  assert.deepEqual(out.results.map((r) => r.verdict), ["ACCEPTED", "ACCEPTED"]);
  assert.deepEqual(out.warnings, ["AC02: SAME_OUTPUT as AC01."]);
});

test("why texts never echo user free text", () => {
  const s = state([["test", "local"]]);
  const marker = "SENTINEL_XYZZY";
  const out = applyEvidence(s, [run(`${marker}\n${PYTEST_FAIL}`, 0, { cmd: marker })]);
  assert.ok(!JSON.stringify(out).includes(marker));
});

test("public host classification without DNS", () => {
  for (const h of ["localhost", "app.localhost", "printer.local", "db.internal", "0.0.0.0", "127.0.0.5", "10.1.2.3", "172.20.0.1", "192.168.1.1", "169.254.1.1", "[::1]", "fd00::1", "intranet"]) {
    assert.equal(isPublicHost(h), false, h);
  }
  for (const h of ["example.com", "8.8.8.8", "172.32.0.1", "[2001:db8::1]"]) assert.equal(isPublicHost(h), true, h);
});

test("level satisfaction rules", () => {
  assert.ok(levelSatisfies("production", "deployed"));
  assert.ok(levelSatisfies("production", "delivered"));
  assert.ok(!levelSatisfies("deployed", "delivered"));
  assert.ok(!levelSatisfies("production", "user"));
  assert.ok(levelSatisfies("user", "user"));
  assert.ok(!levelSatisfies("local", "deployed"));
});
