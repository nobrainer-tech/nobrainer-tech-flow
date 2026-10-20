// Evidence verdicts, staleness and the failure budget (spec section 7).
import { createHash } from "node:crypto";
import { classifyUrl, kindMatches, levelSatisfies, type Level, type Proof } from "../rules/levels.ts";
import { hasFailingSummary, parseTestSummary } from "./parsers.ts";
import { normaliseOut, normaliseText } from "./normalise.ts";
import { MAX_FILES, hex8, itemId, type Item, type TokenState } from "../token.ts";

export type EvidenceRecord = {
  item: string;
  kind: Proof;
  cmd?: string | undefined;
  exit?: number | undefined;
  out?: string | undefined;
  passed?: number | undefined;
  failed?: number | undefined;
  path?: string | undefined;
  sha256?: string | undefined;
  url?: string | undefined;
  status?: number | undefined;
  note?: string | undefined;
};

export type RecordResult = {
  item: string;
  verdict: "ACCEPTED" | "FAILED" | "REJECTED";
  level?: Level;
  digest?: string;
  code?: string;
  why?: string;
};

const sha = (s: string): Buffer => createHash("sha256").update(s).digest();

export function recordDigest(r: EvidenceRecord): Buffer {
  // The note is part of the digest so two different observations never share one (spec 7.1 amended).
  const parts = [r.kind, r.cmd ?? "", r.exit ?? "", normaliseOut(r.out ?? ""), r.path ?? "", r.sha256 ?? "", r.url ?? "", r.status ?? "", normaliseText(r.note ?? "")];
  return sha(parts.join("|")).subarray(0, 4);
}

/** Is an accepted item's proof stale because a registered file changed after it? */
export function isStale(item: Item, epoch: number): boolean {
  return item.status === "ACCEPTED" && (item.kind === "test" || item.kind === "command") && item.epoch < epoch;
}

export const isCurrent = (item: Item, epoch: number): boolean => item.status === "ACCEPTED" && !isStale(item, epoch);

/** One identity per file: forward slashes, no empty or "." segments (".." is kept, then rejected). */
function normalisePath(p: string): string {
  const unix = p.trim().replace(/\\/g, "/");
  const segments = unix.split("/").filter((s) => s !== "" && s !== ".");
  return (unix.startsWith("/") ? "/" : "") + segments.join("/");
}

/** Reopen every accepted test or command result (used when the change epoch cannot grow). */
function staleAllRuns(state: TokenState): void {
  for (const item of state.items) {
    if (item.status === "ACCEPTED" && (item.kind === "test" || item.kind === "command")) {
      Object.assign(item, { status: "OPEN", kind: null, digest: Buffer.alloc(4) });
    }
  }
}

/** Register a file hash; a different hash for a known path increments the change epoch. */
function registerFile(state: TokenState, path: string, sha256: string): void {
  const ph = sha(normalisePath(path)).subarray(0, 4);
  const ch = Buffer.from(sha256.slice(0, 8), "hex");
  const known = state.files.find((f) => f.path.equals(ph));
  if (known) {
    if (!known.hash.equals(ch)) {
      known.hash = ch;
      if (state.epoch < 255) state.epoch += 1;
      else staleAllRuns(state); // the epoch byte is full: invalidate directly so staleness is never missed
    }
    return;
  }
  if (state.files.length >= MAX_FILES) state.files.shift(); // oldest evicted (documented limit)
  state.files.push({ path: ph, hash: ch });
}

const INVALIDATING = new Set(["COUNTS_MISMATCH", "EXIT_OUTPUT_CONFLICT", "NO_TESTS_RAN"]);

type Outcome = { pass: true; level: Level } | { pass: false; failed: true } | { reject: string; why: string };

const reject = (code: string, why: string): Outcome => ({ reject: code, why });

function judgeRun(r: EvidenceRecord, id: string): Outcome {
  if (!r.cmd?.trim() || r.exit === undefined || (r.kind === "test" && r.out === undefined)) {
    return reject("MISSING_FIELD", `${id}: ${r.kind} evidence needs cmd, exit${r.kind === "test" ? " and out" : ""}.`);
  }
  const out = normaliseOut(r.out ?? "");
  if (r.kind === "command") {
    if (r.exit !== 0) return { pass: false, failed: true };
    if (hasFailingSummary(out)) return reject("EXIT_OUTPUT_CONFLICT", `${id}: exit 0 but the output has a failing test summary.`);
  } else {
    const s = parseTestSummary(out);
    if (s && ((r.passed !== undefined && r.passed !== s.passed) || (r.failed !== undefined && r.failed !== s.failed))) {
      return reject("COUNTS_MISMATCH", `${id}: claimed counts differ from the output (${s.passed} passed, ${s.failed} failed).`);
    }
    if (r.exit !== 0) return { pass: false, failed: true };
    if (!s) return reject("NO_TEST_SUMMARY", `${id}: no recognised test summary; include the summary line, or submit it as kind command.`);
    if (s.failed > 0) return reject("EXIT_OUTPUT_CONFLICT", `${id}: exit 0 but the summary has ${s.failed} failed.`);
    if (s.passed < 1) return reject("NO_TESTS_RAN", `${id}: the summary shows no passed tests.`);
  }
  // Optional location metadata must not conceal a failed or zero-pass rerun.
  let level: Level = "local";
  if (r.url !== undefined) {
    const u = classifyUrl(r.url);
    if (!u.ok) return reject("BAD_URL", `${id}: url must be an http or https URL.`);
    if (u.https && u.publicHost) level = "deployed";
  }
  return { pass: true, level };
}

function judge(r: EvidenceRecord, id: string): Outcome {
  switch (r.kind) {
    case "test":
    case "command":
      return judgeRun(r, id);
    case "file":
      return { pass: true, level: "static" };
    case "url": {
      if (r.url === undefined || r.status === undefined) return reject("MISSING_FIELD", `${id}: url evidence needs url and status.`);
      const u = classifyUrl(r.url);
      if (!u.ok) return reject("BAD_URL", `${id}: url must be an http or https URL.`);
      if (u.publicHost && !u.https) return reject("NOT_HTTPS", `${id}: a public URL must use https.`);
      if (r.status < 200 || r.status > 399) return { pass: false, failed: true };
      return { pass: true, level: u.publicHost ? "production" : "local" };
    }
    case "observation": {
      const n = (r.note ?? "").trim().length;
      if (n < 20) return reject("NOTE_TOO_SHORT", `${id}: an observation needs a note of at least 20 characters.`);
      return { pass: true, level: "user" };
    }
  }
}

export type EvidenceOutcome = { results: RecordResult[]; repeated: boolean; warnings: string[] };

/** Apply records in order to `state` (mutated). Item IDs must already be validated. */
export function applyEvidence(state: TokenState, records: EvidenceRecord[]): EvidenceOutcome {
  const results: RecordResult[] = [];
  let repeated = false;
  for (const r of records) {
    const index = Number(r.item.slice(2)) - 1;
    const item = state.items[index] as Item;
    const id = itemId(index);
    if (r.kind === "file") {
      if (!r.path?.trim() || !normalisePath(r.path) || r.sha256 === undefined) {
        results.push({ item: id, verdict: "REJECTED", code: "MISSING_FIELD", why: `${id}: file evidence needs path and sha256.` });
        continue;
      }
      if (normalisePath(r.path).split("/").includes("..")) {
        results.push({ item: id, verdict: "REJECTED", code: "BAD_PATH", why: `${id}: path must not contain .. segments.` });
        continue;
      }
    }
    if (!kindMatches(r.kind, item.proof)) {
      results.push({ item: id, verdict: "REJECTED", code: "KIND_MISMATCH", why: `${id} needs ${item.proof} evidence, not ${r.kind}.` });
      continue;
    }
    // Only accepted-shape file evidence for a file item may change the registry (and so stale runs).
    if (r.kind === "file") registerFile(state, r.path as string, r.sha256 as string);
    const o = judge(r, id);
    if ("reject" in o) {
      results.push({ item: id, verdict: "REJECTED", code: o.reject, why: o.why });
      // A run that fails, contradicts itself or passes no tests withdraws acceptance; only a
      // later consistent pass can accept the item again. It does not count toward the failure budget.
      if (INVALIDATING.has(o.reject)) Object.assign(item, { status: "FAILED", kind: r.kind, digest: recordDigest(r), epoch: state.epoch });
      continue;
    }
    const digest = recordDigest(r);
    if (!o.pass) {
      item.failures = Math.min(3, item.failures + 1);
      Object.assign(item, { status: "FAILED", kind: r.kind, digest, epoch: state.epoch });
      const res: RecordResult = { item: id, verdict: "FAILED", digest: hex8(digest) };
      if (item.failures >= 2) {
        res.code = "REPEATED_DEFECT";
        repeated = true;
      }
      results.push(res);
      continue;
    }
    if (!levelSatisfies(o.level, item.level)) {
      results.push({ item: id, verdict: "REJECTED", code: "LEVEL_TOO_LOW", why: `${id} needs ${item.level}; this evidence proves ${o.level}.` });
      continue;
    }
    Object.assign(item, { status: "ACCEPTED", kind: r.kind, digest, epoch: state.epoch });
    results.push({ item: id, verdict: "ACCEPTED", level: o.level, digest: hex8(digest) });
  }
  return { results, repeated, warnings: sameOutputWarnings(state) };
}

function sameOutputWarnings(state: TokenState): string[] {
  const out: string[] = [];
  const zero = Buffer.alloc(4);
  state.items.forEach((a, i) => {
    if (a.status !== "ACCEPTED" || a.digest.equals(zero)) return;
    const j = state.items.findIndex((b, k) => k < i && b.status === "ACCEPTED" && b.digest.equals(a.digest));
    if (j >= 0) out.push(`${itemId(i)}: SAME_OUTPUT as ${itemId(j)}.`);
  });
  return out;
}
