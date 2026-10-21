// draft_flow_handoff (spec 5.5). Built only from the receipt; never contains user text.
import * as z from "zod";
import { RECEIPT_PREFIX, hex8, itemId, type Item } from "../token.ts";
import { FLOW_VERSION } from "../content/cards.ts";
import { openToken, tokenField, type ToolDef } from "./common.ts";

const input = z.strictObject({ receipt: tokenField });

const PLACEHOLDER: Record<string, string> = {
  test: "<command and result>",
  command: "<command and result>",
  file: "<file path>",
  url: "<URL and status>",
  observation: "<what was observed>",
};

function proofLine(it: Item, i: number): string {
  const kind = it.kind ?? it.proof;
  const state = kind === "observation" ? "self-attested" : "accepted";
  return `- ${itemId(i)} ${kind}, ${it.level}, ${state} (digest ${hex8(it.digest)}): ${PLACEHOLDER[kind]}`;
}

export const handoffTool: ToolDef<typeof input> = {
  name: "draft_flow_handoff",
  title: "Draft the final handoff",
  description:
    "Use after check_flow_done. Returns a short final-report skeleton from the done receipt: delivered outcome, proof per DoD item, what was not checked, decisions left to the user and the next action.",
  input,
  async run(args, ctx) {
    const state = await openToken(args.receipt, RECEIPT_PREFIX, ctx);
    const proof = state.items.flatMap((it, i) => (it.unchecked ? [] : [proofLine(it, i)]));
    const gaps = state.items.flatMap((it, i) => (it.unchecked ? [`- ${itemId(i)}: <reason>`] : []));
    const sections = [
      "## Delivered\n<one sentence: the observable outcome>",
      `## Proof\n${proof.join("\n") || "- None"}`,
      `## Not checked\n${gaps.join("\n") || "- Nothing"}`,
      "## Decisions left to you\n<owner decisions, or 'None'>",
      "## Next action\n<one action, or 'None'>",
      `Contract ${hex8(state.contract)}, Flow ${FLOW_VERSION}. Evidence was reported by the agent; the server checked consistency, not truth.`,
    ];
    return { verdict: state.verdict, markdown: sections.join("\n\n") };
  },
};
