// check_flow_done (spec 5.4).
import * as z from "zod";
import { isCurrent, isStale } from "../evidence/checks.ts";
import { CONTRACT_PREFIX, RECEIPT_PREFIX, encodeToken, itemId, renew } from "../token.ts";
import { checkItems, itemField, openToken, tokenField, type ToolDef } from "./common.ts";

const input = z.strictObject({
  token: tokenField,
  unchecked: z.array(z.strictObject({ item: itemField, reason: z.string().min(10).max(200) })).max(10).optional(),
});

export const doneTool: ToolDef<typeof input> = {
  name: "check_flow_done",
  title: "Check whether the task is done",
  description:
    "Use before saying a task is done. Returns DONE only when every DoD item has accepted, current evidence, DONE_WITH_GAPS when the rest are listed in unchecked with a reason, otherwise NOT_DONE with the exact missing items.",
  input,
  async run(args, ctx) {
    const state = await openToken(args.token, CONTRACT_PREFIX, ctx);
    const listed = new Set((args.unchecked ?? []).filter((u) => u.reason.trim().length >= 10).map((u) => u.item));
    checkItems(state, [...listed]);
    const missing: Array<{ item: string; need: string }> = [];
    const stale: Array<{ item: string; why: string }> = [];
    const unchecked: string[] = [];
    state.items.forEach((it, i) => {
      const id = itemId(i);
      it.unchecked = false;
      if (isCurrent(it, state.epoch)) return;
      if (listed.has(id)) {
        it.unchecked = true;
        unchecked.push(id);
      } else if (isStale(it, state.epoch)) {
        stale.push({ item: id, why: "a registered file changed after this check ran; re-run it" });
      } else {
        const failed = it.status === "FAILED" ? "; the last record failed" : "";
        missing.push({ item: id, need: `${it.proof} evidence, level ${it.level}${failed}` });
      }
    });
    const verdict = missing.length || stale.length ? "NOT_DONE" : unchecked.length ? "DONE_WITH_GAPS" : "DONE";
    const result: Record<string, unknown> = { verdict, missing, stale, unchecked };
    if (verdict !== "NOT_DONE") {
      const receipt = { ...renew(state, ctx.now()), verdict: verdict as "DONE" | "DONE_WITH_GAPS" };
      result.receipt = encodeToken(receipt, RECEIPT_PREFIX, ctx.ring);
      result.next = "draft_flow_handoff";
    }
    return result;
  },
};
