// Response serialisation with a byte cap and fixed-order shaping (spec 10.2).
import { ToolError } from "./errors.ts";

export const MAX_RESPONSE_BYTES = 1500;

/** Compact JSON, ASCII only (non-ASCII is escaped as \uXXXX). */
export function toAscii(value: unknown): string {
  return JSON.stringify(value).replace(/[\u007f-￿]/g, (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}`);
}

type Shapeable = Record<string, unknown>;

function cut(list: unknown[], keep: number): unknown[] {
  return list.length > keep ? [...list.slice(0, keep), `+${list.length - keep} more`] : list;
}

/** Serialise; if over the cap, shape in a fixed order (lint, rules, lists, optional guidance). Token and verdict stay. */
export function serialise(result: Shapeable, cap = MAX_RESPONSE_BYTES): string {
  let text = toAscii(result);
  if (text.length <= cap) return text;
  const shaped: Shapeable = structuredClone(result);
  const steps: Array<(r: Shapeable) => void> = [
    (r) => { if (Array.isArray(r.lint)) r.lint = cut(r.lint, 3); },
    (r) => {
      if (Array.isArray(r.rules)) r.rules = r.rules.slice(0, 3);
      const next = r.next as Shapeable | undefined;
      if (next && Array.isArray(next.rules)) next.rules = next.rules.slice(0, 3);
    },
    (r) => {
      for (const k of ["missing", "stale", "results", "warnings", "shortlist"]) {
        if (Array.isArray(r[k])) r[k] = cut(r[k] as unknown[], 5);
      }
    },
    // Optional guidance goes next: the next step keeps its stage and source, the rules can be
    // fetched with get_flow_step. Items become "AC01 url production"; lint keeps its first entry.
    (r) => {
      const next = r.next as Shapeable | undefined;
      if (next && Array.isArray(next.rules)) delete next.rules;
    },
    (r) => {
      if (Array.isArray(r.items)) {
        r.items = r.items.map((i) => (i && typeof i === "object" ? Object.values(i as object).join(" ") : i));
      }
      if (Array.isArray(r.lint)) r.lint = cut(r.lint, 1);
    },
  ];
  for (const step of steps) {
    step(shaped);
    text = toAscii(shaped);
    if (text.length <= cap) return text;
  }
  throw new ToolError("BUDGET_EXCEEDED", "the result is larger than the response budget", "send fewer records or items per call");
}
