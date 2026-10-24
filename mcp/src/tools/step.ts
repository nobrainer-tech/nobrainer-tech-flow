// get_flow_step (spec 5.2).
import * as z from "zod";
import { CONTRACT_PREFIX, encodeToken, itemId, renew, type TokenState } from "../token.ts";
import { FLOW_VERSION, MODULES, getCard } from "../content/cards.ts";
import { isCurrent, isStale } from "../evidence/checks.ts";
import { ToolError } from "../errors.ts";
import { contractId, openToken, tokenField, type ToolContext, type ToolDef } from "./common.ts";

export const STAGES = ["DRIFT_CHECK", "BUDDY", "SCOPE", "AUTOPILOT", "VERIFY", "RECEIVE_AUDIT", "LEARN"] as const;
export const EVENTS = ["blocked", "review_failed", "decision_changed", "worker_reported", "repeated_failure", "resume"] as const;

const input = z.strictObject({
  token: tokenField.optional(),
  stage: z.enum(STAGES).optional(),
  event: z.enum(EVENTS).optional(),
  module: z.string().regex(/^nobrainer-[a-z-]{2,40}$/).optional(),
});

type StateCard = "event:repeated_failure" | "stage:RECEIVE_AUDIT" | "stage:AUTOPILOT" | "stage:VERIFY";

/** Pick the next card from token state (spec 5.2 table). */
export function cardForState(state: TokenState): { id: StateCard; next?: string } {
  const items = state.items;
  if (items.some((i) => i.failures >= 2 && !isCurrent(i, state.epoch))) return { id: "event:repeated_failure" };
  if (items.every((i) => isCurrent(i, state.epoch))) return { id: "stage:RECEIVE_AUDIT", next: "check_flow_done" };
  if (items.every((i) => i.status === "OPEN" && i.failures === 0)) return { id: "stage:AUTOPILOT" };
  return { id: "stage:VERIFY" };
}

const NEXT_SAFE_ACTION: Record<StateCard, string> = {
  "event:repeated_failure": "run nobrainer-rca on the item that failed twice before retrying it",
  "stage:RECEIVE_AUDIT": "call check_flow_done",
  "stage:AUTOPILOT": "do the work, run the checks, then call check_flow_evidence",
  "stage:VERIFY": "run the checks for items not ACCEPTED, then call check_flow_evidence",
};

/**
 * Goal-file block built from token state only. The server never repeats user text, so OUTCOME
 * and NON_GOALS stay placeholders; the renewed contract travels as FLOW_CONTRACT.
 */
export function goalBlock(state: TokenState, ctx: ToolContext): string {
  const renewed = renew(state, ctx.now());
  const rows = state.items.map((it, i) => {
    const status = isCurrent(it, state.epoch) ? "ACCEPTED" : isStale(it, state.epoch) ? "STALE" : it.status === "FAILED" ? "FAILED" : "OPEN";
    return `- ${itemId(i)} ${it.proof}, ${it.level}: ${status}`;
  });
  const accepted = state.items.filter((it) => isCurrent(it, state.epoch)).length;
  const expires = new Date(renewed.expires * 1000).toISOString().slice(0, 10);
  return [
    `GOAL_ID: flow-${contractId(state)}`,
    "OUTCOME: <your outcome; the server does not keep it>",
    "NON_GOALS: <your non-goals, or NONE>",
    "DOD:",
    ...rows,
    "STATUS: ACTIVE",
    `CHECKPOINT: ${accepted} of ${state.items.length} accepted, contract expires ${expires}`,
    `NEXT_SAFE_ACTION: ${NEXT_SAFE_ACTION[cardForState(state).id]}`,
    `FLOW_CONTRACT: ${encodeToken(renewed, CONTRACT_PREFIX, ctx.ring)}`,
  ].join("\n");
}

export const stepTool: ToolDef<typeof input> = {
  name: "get_flow_step",
  title: "Get the next Flow step",
  description:
    "Use when you need guidance for the current Flow stage, an event (for example blocked) or one Flow module (for example nobrainer-review). Returns up to six rules quoted from the pinned Flow release, with their source. With a contract token, event resume also returns a goal block to save.",
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
    // Resume with a token: two rules plus the goal block keep a 10-item answer within 1,500 bytes.
    const goal = state && id === "event:resume" ? goalBlock(state, ctx) : undefined;
    const out: Record<string, unknown> = { card: id, flow_version: FLOW_VERSION };
    if (card.description) out.description = card.description;
    out.rules = goal ? card.rules.slice(0, 2) : card.rules;
    out.source = card.source;
    if (card.full) out.full = card.full;
    const hint = next ?? card.next;
    if (hint) out.next = hint;
    if (goal) out.goal_block = goal;
    return out;
  },
};
