// check_flow_done (spec 5.4).
import * as z from "zod";
import { itemState } from "../evidence/checks.ts";
import { CONTRACT_PREFIX, RECEIPT_PREFIX, encodeToken, itemId, renew } from "../token.ts";
import { checkItems, itemField, openToken, tokenField, type ToolDef } from "./common.ts";

const input = z.strictObject({
  token: tokenField.describe("Latest contract token"),
  unchecked: z.array(z.strictObject({ item: itemField, reason: z.string().trim().min(10).max(200) })).max(10).optional(),
});

export const doneTool: ToolDef<typeof input> = {
  name: "check_flow_done",
  title: "Check whether the task is done",
  description:
    "Use before saying a task is done. Returns DONE only when every DoD item has accepted, current evidence, DONE_WITH_GAPS when the rest are listed in unchecked with a reason, otherwise NOT_DONE with the exact missing items.",
  input,
  async run(args, ctx) {
    const state = await openToken(args.token, CONTRACT_PREFIX, ctx);
    const listed = new Set((args.unchecked ?? []).map((u) => u.item));
    checkItems(state, [...listed]);
    const missing: Array<{ item: string; need: string }> = [];
    const stale: Array<{ item: string; why: string }> = [];
    const unchecked: string[] = [];
    const withdrawn: number[] = [];
    state.items.forEach((it, i) => {
      const id = itemId(i);
      const st = itemState(it, state.epoch);
      if (st === "ACCEPTED" && listed.has(id)) withdrawn.push(i);
      // Listing an accepted item withdraws it: after a resume or handoff the agent may no longer
      // hold the evidence it once submitted, and a summary of it is not proof.
      it.unchecked = listed.has(id);
      if (st === "ACCEPTED" && !it.unchecked) return;
      if (it.unchecked) {
        unchecked.push(id);
      } else if (st === "STALE") {
        stale.push({ item: id, why: "a registered file changed after this check ran; re-run it" });
      } else {
        const failed = st === "FAILED" ? "; the last record failed or was inconsistent" : "";
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
    if (withdrawn.length) {
      // The withdrawal must survive a resume: return a contract token where those items are open again.
      for (const i of withdrawn) Object.assign(state.items[i] as object, { status: "OPEN", unchecked: false, digest: Buffer.alloc(4) });
      for (const it of state.items) it.unchecked = false;
      result.token = encodeToken(renew(state, ctx.now()), CONTRACT_PREFIX, ctx.ring);
      result.note = "Use this token from now on: the one you sent still holds the withdrawn proof.";
    }
    return result;
  },
};
