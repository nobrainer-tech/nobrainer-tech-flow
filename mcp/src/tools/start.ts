// start_flow_task (spec 5.1).
import { createHash, randomBytes } from "node:crypto";
import * as z from "zod";
import { LEVELS, PROOFS, RISKS } from "../rules/levels.ts";
import { choosePath, flowTriple, lint, needsGates, normaliseItems, normaliseText, route, versionNote } from "../rules/contract.ts";
import { CONTRACT_PREFIX, LIFETIME_S, encodeToken, itemId, type TokenState } from "../token.ts";
import { FLOW_VERSION, getCard } from "../content/cards.ts";
import { ToolError } from "../errors.ts";
import type { ToolDef } from "./common.ts";

const input = z.strictObject({
  outcome: z.string().max(300).describe("Observable result and who sees it"),
  dod: z
    .array(z.strictObject({ text: z.string().max(160), proof: z.enum(PROOFS), level: z.enum(LEVELS).optional() }))
    .min(1)
    .max(10),
  non_goals: z.array(z.string().max(120)).max(5).optional(),
  risks: z.array(z.enum(RISKS)).max(6).optional(),
  local_flow: z.string().max(20).optional().describe("Version of a locally loaded Flow skill, if any"),
});

export const startTool: ToolDef<typeof input> = {
  name: "start_flow_task",
  title: "Start a Flow task",
  description:
    "Use at the start of a non-trivial task. Checks your proposed outcome and definition of done (DoD) against Flow's contract rules, chooses the quick or full path, and returns DoD item IDs, a signed contract token and the first step. Computes only; stores nothing.",
  input,
  run(args, ctx) {
    const outcome = normaliseText(args.outcome);
    if (!outcome) throw new ToolError("INVALID_INPUT", "outcome is empty", "state the observable result and who sees it");
    const items = normaliseItems(args.dod);
    const risks = [...new Set(args.risks ?? [])];
    const nonGoals = (args.non_goals ?? []).map(normaliseText).filter(Boolean);
    const path = choosePath(items, risks);
    const now = ctx.now();
    const canonical = JSON.stringify({ outcome, items, nonGoals, risks: [...risks].sort() });
    const contract = createHash("sha256").update(canonical).update(randomBytes(4)).digest().subarray(0, 8);
    const state: TokenState = {
      kid: ctx.ring.signer,
      full: path === "FULL",
      verdict: "NONE",
      risks,
      contract,
      created: now,
      expires: now + LIFETIME_S,
      flow: flowTriple(FLOW_VERSION),
      epoch: 0,
      items: items.map((i) => ({
        proof: i.proof, level: i.level, failures: 0, status: "OPEN", kind: null, unchecked: false, epoch: 0, digest: Buffer.alloc(4),
      })),
      files: [],
    };
    const routing = route(path, risks, items);
    const drift = getCard("stage:DRIFT_CHECK");
    const result: Record<string, unknown> = {
      path,
      flow_version: FLOW_VERSION,
      contract: contract.subarray(0, 4).toString("hex"),
      items: items.map((i, n) => ({ id: itemId(n), proof: i.proof, level: i.level })),
    };
    const warnings = lint(items, path, nonGoals);
    if (warnings.length) result.lint = warnings;
    result.modules = routing.modules;
    if (routing.optional.length) result.optional = routing.optional;
    if (needsGates(risks)) result.gates = getCard("gates")?.rules ?? [];
    const note = versionNote(args.local_flow, FLOW_VERSION);
    if (note) result.version_note = note;
    if (drift) result.next = { stage: "DRIFT_CHECK", rules: drift.rules.slice(0, 2), source: drift.source };
    result.token = encodeToken(state, CONTRACT_PREFIX, ctx.ring);
    return result;
  },
};
