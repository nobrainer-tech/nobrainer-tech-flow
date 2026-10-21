// Shared tool plumbing: context, token access, input validation and JSON Schema export.
import * as z from "zod";
import { ToolError } from "../errors.ts";
import { decodeToken, hex8, itemId, type KeyRing, type TokenState } from "../token.ts";
import type { RateLimiter } from "../ratelimit.ts";

export type ToolContext = {
  ring: KeyRing;
  now: () => number; // Unix seconds
  limiter: RateLimiter;
  request?: Request | undefined;
};

export type ToolDef<S extends z.ZodObject = z.ZodObject> = {
  name: string;
  title: string;
  description: string;
  input: S;
  run: (args: z.output<S>, ctx: ToolContext) => Promise<Record<string, unknown>> | Record<string, unknown>;
};

export const ANNOTATIONS = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
} as const;

export const tokenField = z.string().max(2048);
export const itemField = z.string().regex(/^AC[0-9]{2}$/);

/** Decode a token, then apply the per-contract rate limit keyed by the contract digest. */
export async function openToken(token: string, prefix: string, ctx: ToolContext): Promise<TokenState> {
  const state = decodeToken(token.trim(), prefix, ctx.ring, ctx.now());
  if (await ctx.limiter(state.contract.toString("hex"), ctx.request)) {
    throw new ToolError("RATE_LIMITED", "this contract reached 60 calls in 10 minutes", "retry after 60 s");
  }
  return state;
}

export function checkItems(state: TokenState, ids: string[]): void {
  const n = state.items.length;
  for (const id of ids) {
    const i = Number(id.slice(2));
    if (i < 1 || i > n) {
      throw new ToolError("UNKNOWN_ITEM", "an item ID is not in the contract", `valid items: AC01-${itemId(n - 1)}`);
    }
  }
}

export const contractId = (state: TokenState): string => hex8(state.contract);

function issuePath(path: PropertyKey[]): string {
  return path.reduce<string>((acc, p) => (typeof p === "number" ? `${acc}[${p}]` : acc ? `${acc}.${String(p)}` : String(p)), "") || "input";
}

/** Validate with zod and map the first issue to an error that never echoes the received value. */
export function parseArgs<S extends z.ZodObject>(schema: S, raw: unknown): z.output<S> {
  const res = schema.safeParse(raw ?? {});
  if (res.success) return res.data;
  const issue = res.error.issues[0] as z.core.$ZodIssue;
  const where = issuePath(issue.path);
  if (issue.code === "too_big" && issue.origin === "string") {
    throw new ToolError("INPUT_TOO_LARGE", `${where} is longer than ${String(issue.maximum)} characters`, where.endsWith(".out") ? "send only the last lines of output, max 4000 characters" : `shorten ${where} to ${String(issue.maximum)} characters`);
  }
  if (issue.code === "too_big") {
    throw new ToolError("INPUT_TOO_LARGE", `${where} has more than ${String(issue.maximum)} entries`, `send at most ${String(issue.maximum)}`);
  }
  let fix = `correct ${where} to match the tool schema`;
  if (issue.code === "invalid_value") fix = `${where} must be one of ${issue.values.map(String).join(", ")}`;
  else if (issue.code === "unrecognized_keys") fix = `remove properties that are not in the tool schema at ${where}`;
  else if (issue.code === "invalid_type") fix = `${where} must be ${issue.expected}`;
  else if (issue.code === "too_small") fix = `${where} needs at least ${String(issue.minimum)}`;
  else if (issue.code === "invalid_format") fix = `${where} has the wrong format`;
  throw new ToolError("INVALID_INPUT", `${where} is invalid`, fix);
}

const SAFE_INT = 9007199254740991;

/** Compact JSON Schema for tools/list: no $schema, no default safe-integer bounds. */
export function jsonSchemaOf(schema: z.ZodObject): Record<string, unknown> {
  const out = z.toJSONSchema(schema, { target: "draft-2020-12", io: "input" }) as Record<string, unknown>;
  delete out.$schema;
  const walk = (node: unknown): void => {
    if (!node || typeof node !== "object") return;
    const o = node as Record<string, unknown>;
    if (o.minimum === -SAFE_INT) delete o.minimum;
    if (o.maximum === SAFE_INT) delete o.maximum;
    if (Array.isArray(o.enum) && o.type === "string") delete o.type;
    Object.values(o).forEach(walk);
  };
  walk(out);
  return out;
}
