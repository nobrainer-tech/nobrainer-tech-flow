// check_flow_evidence (spec 5.3).
import * as z from "zod";
import { PROOFS } from "../rules/levels.ts";
import { applyEvidence, isCurrent, isStale } from "../evidence/checks.ts";
import { CONTRACT_PREFIX, encodeToken, itemId, renew } from "../token.ts";
import { checkItems, itemField, openToken, tokenField, type ToolDef } from "./common.ts";

const record = z.strictObject({
  item: itemField,
  kind: z.enum(PROOFS),
  cmd: z.string().max(300).optional(),
  exit: z.int().optional(),
  out: z.string().max(4000).optional().describe("Last lines of output, including the summary line"),
  passed: z.int().min(0).optional(),
  failed: z.int().min(0).optional(),
  path: z.string().max(300).optional(),
  sha256: z.string().regex(/^[0-9a-f]{64}$/).optional(),
  url: z.string().max(500).optional(),
  status: z.int().optional(),
  note: z.string().max(300).optional(),
});

const input = z.strictObject({
  token: tokenField.describe("Contract token from start_flow_task or the last check"),
  evidence: z.array(record).min(1).max(4),
});

export const evidenceTool: ToolDef<typeof input> = {
  name: "check_flow_evidence",
  title: "Check evidence for DoD items",
  description:
    "Use after running a check. Validates one to four evidence records against DoD items in the contract token: exit codes, test counts in the output, hashes, URL status and evidence level. It cannot see your machine; it checks structure and consistency only. Returns verdicts and an updated token.",
  input,
  async run(args, ctx) {
    const state = await openToken(args.token, CONTRACT_PREFIX, ctx);
    checkItems(state, args.evidence.map((r) => r.item));
    const outcome = applyEvidence(state, args.evidence);
    const result: Record<string, unknown> = { results: outcome.results };
    result.open = state.items.flatMap((it, i) => (isCurrent(it, state.epoch) ? [] : [itemId(i)]));
    const stale = state.items.flatMap((it, i) => (isStale(it, state.epoch) ? [itemId(i)] : []));
    if (stale.length) result.stale = stale;
    if (outcome.warnings.length) result.warnings = outcome.warnings;
    if (outcome.repeated) result.next = { event: "repeated_failure", module: "nobrainer-rca" };
    result.token = encodeToken(renew(state, ctx.now()), CONTRACT_PREFIX, ctx.ring);
    return result;
  },
};
