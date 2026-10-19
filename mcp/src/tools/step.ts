// get_flow_step (spec 5.2).
import * as z from "zod";
import { CONTRACT_PREFIX, type TokenState } from "../token.ts";
import { FLOW_VERSION, MODULES, getCard } from "../content/cards.ts";
import { isCurrent } from "../evidence/checks.ts";
import { ToolError } from "../errors.ts";
import { openToken, tokenField, type ToolDef } from "./common.ts";

export const STAGES = ["DRIFT_CHECK", "BUDDY", "SCOPE", "AUTOPILOT", "VERIFY", "RECEIVE_AUDIT", "LEARN"] as const;
export const EVENTS = ["blocked", "review_failed", "decision_changed", "worker_reported", "repeated_failure", "resume"] as const;

const input = z.strictObject({
  token: tokenField.optional(),
  stage: z.enum(STAGES).optional(),
  event: z.enum(EVENTS).optional(),
  module: z.string().regex(/^nobrainer-[a-z-]{2,40}$/).optional(),
});

/** Pick the next card from token state (spec 5.2 table). */
export function cardForState(state: TokenState): { id: string; next?: string } {
  const items = state.items;
  if (items.some((i) => i.failures >= 2 && !isCurrent(i, state.epoch))) return { id: "event:repeated_failure" };
  if (items.every((i) => isCurrent(i, state.epoch))) return { id: "stage:RECEIVE_AUDIT", next: "check_flow_done" };
  if (items.every((i) => i.status === "OPEN" && i.failures === 0)) return { id: "stage:AUTOPILOT" };
  return { id: "stage:VERIFY" };
}

export const stepTool: ToolDef<typeof input> = {
  name: "get_flow_step",
  title: "Get the next Flow step",
  description:
    "Use when you need guidance for the current Flow stage, an event (for example blocked) or one Flow module (for example nobrainer-review). Returns up to six short rules quoted from the pinned Flow release, with their source. Works with or without a contract token.",
  input,
  async run(args, ctx) {
    let id = "overview";
    let next: string | undefined;
    const state = args.token ? await openToken(args.token, CONTRACT_PREFIX, ctx) : undefined;
    if (args.module) {
      id = `module:${args.module}`;
      if (!MODULES.includes(args.module)) {
        throw new ToolError("UNKNOWN_CARD", "no module card with that name", `valid modules: ${MODULES.join(", ")}`);
      }
    } else if (args.event) id = `event:${args.event}`;
    else if (args.stage) id = `stage:${args.stage}`;
    else if (state) ({ id, next } = cardForState(state));
    const card = getCard(id);
    if (!card) throw new ToolError("UNKNOWN_CARD", "no guidance card for that request", "use a stage, event or module listed in the tool schema");
    const out: Record<string, unknown> = { card: id, flow_version: FLOW_VERSION };
    if (card.description) out.description = card.description;
    out.rules = card.rules;
    out.source = card.source;
    if (card.full) out.full = card.full;
    const hint = next ?? card.next;
    if (hint) out.next = hint;
    return out;
  },
};
