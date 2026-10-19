import { test } from "node:test";
import assert from "node:assert/strict";
import { ROUTED_MODULES, choosePath, lint, needsGates, normaliseItems, route, versionNote } from "../../src/rules/contract.ts";
import { MODULES } from "../../src/content/cards.ts";
import { ToolError } from "../../src/errors.ts";

const items = (...specs: Array<[string, "test" | "file" | "url" | "command" | "observation", string?]>) =>
  normaliseItems(specs.map(([text, proof, level]) => ({ text, proof, level: level as never })));

test("quick path only without risks, at most 3 items, static/local levels", () => {
  assert.equal(choosePath(items(["unit test passes for parse()", "test"]), []), "QUICK");
  assert.equal(choosePath(items(["a", "test"], ["b", "test"], ["c", "test"], ["d", "test"]), []), "FULL");
  assert.equal(choosePath(items(["site is up at https://x.dev", "url"]), []), "FULL");
  assert.equal(choosePath(items(["a", "test"]), ["security"]), "FULL");
});

test("default levels follow the proof kind; unreachable levels are rejected", () => {
  const n = items(["f.md updated", "file"], ["t", "test"], ["https://x.dev ok", "url"], ["user confirmed it", "observation"]);
  assert.deepEqual(n.map((i) => i.level), ["static", "local", "deployed", "user"]);
  assert.throws(() => items(["f.md", "file", "deployed"]), (e: unknown) => e instanceof ToolError && e.code === "INVALID_INPUT");
  assert.throws(() => items(["seen", "observation", "local"]), ToolError);
});

test("normalisation strips control characters and collapses whitespace", () => {
  assert.equal(items(["  a\u0007   b\n\tc ", "test"])[0]?.text, "a b c");
});

test("each lint fires", () => {
  const n = items(["Works.", "test"], ["update the changelog", "file"], ["page loads", "url"], ["works", "test"]);
  const out = lint(n, "FULL", []);
  assert.ok(out.includes("AC01: VAGUE: name the observable check."));
  assert.ok(out.includes("AC02: NO_TARGET: name the file path."));
  assert.ok(out.includes("AC03: NO_TARGET: name the URL or host."));
  assert.ok(out.includes("AC04: DUPLICATE: same text as AC01."));
  assert.ok(out.includes("NO_NON_GOALS: list what this task will not do."));
  assert.deepEqual(lint(items(["CHANGELOG.md has the entry", "file"]), "QUICK", []), []);
});

test("routing table", () => {
  const n = items(["live at https://x.dev", "url", "production"]);
  assert.deepEqual(route("FULL", ["security", "ambiguous", "public_contract", "multi_session"], n), {
    modules: ["nobrainer-build", "nobrainer-review", "nobrainer-security", "nobrainer-decide", "nobrainer-spec-driven-development", "nobrainer-sessions"],
    optional: ["nobrainer-browser"],
  });
  assert.deepEqual(route("QUICK", [], items(["t", "test"])), { modules: [], optional: [] });
});

test("every routed module exists in the pinned release", () => {
  for (const m of ROUTED_MODULES) assert.ok(MODULES.includes(m), m);
});

test("owner gates for irreversible or external effects", () => {
  assert.ok(needsGates(["irreversible"]));
  assert.ok(needsGates(["external_effect"]));
  assert.ok(!needsGates(["security"]));
});

test("version note only for older or malformed local versions", () => {
  assert.match(versionNote("2.3.2", "2.4.1") ?? "", /older than 2\.4\.1/);
  assert.equal(versionNote("2.4.1", "2.4.1"), undefined);
  assert.equal(versionNote("v2.5.0", "2.4.1"), undefined);
  assert.match(versionNote("latest", "2.4.1") ?? "", /not a version/);
  assert.equal(versionNote(undefined, "2.4.1"), undefined);
});
